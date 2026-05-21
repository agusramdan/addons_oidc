# -*- coding: utf-8 -*-

import base64
import logging
import jwt
import time

from datetime import datetime, timedelta

from jwt import InvalidTokenError
from odoo import api, fields, models
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)

REDIRECT_MODE = {
   'auth_oauth_oidc': '/auth_oauth/oidc',
   'auth_oauth_oea': '/auth_oauth/oea',
}


class OidcClient(models.Model):
    _name = 'oidc.client'
    _description = 'OIDC Client'

    active = fields.Boolean(default=True)
    name = fields.Char()

    client_id = fields.Char(
        "Client ID",
        help="Use web.base.url + redirect_path as redirect_uri if redirect_uri is not set."
    )
    client_secret = fields.Char()
    web_base_url = fields.Char()
    redirect_uri = fields.Text()
    redirect_path = fields.Selection(
        selection=REDIRECT_MODE.items(),
        default='auth_oauth_oidc'
    )

    def validate_redirect_uri(self, redirect_uri):
        if self.redirect_path:
            return True

        if not self.redirect_uri or not redirect_uri:
            return True

        parsed = urlparse(
            redirect_uri
        )

        if not parsed.scheme:
            _logger.error("Error %s parsed.scheme. %s", parsed.scheme, redirect_uri)
            return False

        if not parsed.netloc:
            _logger.error("Error %s parsed.netloc. %s", parsed.netloc, redirect_uri)
            return False
        # client.redirect_uri_ids
        # .mapped('uri')
        allowed_uris = (self.redirect_uri.splitlines() or []) + [self.redirect_uri]
        normalized_redirect = (
            f'{parsed.scheme}://'
            f'{parsed.netloc}'
            f'{parsed.path}'
        ).strip()

        for allowed_uri in allowed_uris:

            allowed_parsed = urlparse(
                allowed_uri
            )

            normalized_allowed = (
                f'{allowed_parsed.scheme}://'
                f'{allowed_parsed.netloc}'
                f'{allowed_parsed.path}'
            ).strip()

            if normalized_allowed == normalized_redirect:
                return True
            _logger.error("Error [%s] != [%s]", normalized_redirect, normalized_allowed)

        _logger.error("Error %s .", normalized_redirect)

        return False

    def client_auth(self, token):
        try:
            decoded = base64.b64decode(token).decode()
            client_id, client_secret = decoded.split(':', 1)
            client = self.sudo().search([('client_id', '=', client_id)], limit=1)
            if client and client.client_secret == client_secret:
                return client
            else:
                return None
        except:
            return None

    def create_authorization_code(self, redirect_uri=None, scope=''):
        if self.redirect_path:
            redirect_uri = self.web_base_url + REDIRECT_MODE.get(self.redirect_path)
        else:
            redirect_uri = redirect_uri or self.redirect_uri
        return self.env['oidc.authorization.code'].sudo().create({
            'client_id': self.client_id,
            'user_id': self.env.user.id,
            'redirect_uri': redirect_uri,
            'scope': scope,
            'expired_at': fields.Datetime.now() + timedelta(minutes=5)
        })

    def create_access_token(self, redirect_uri=None, scope='',**kw):
        if self.redirect_path:
            redirect_uri = self.web_base_url + REDIRECT_MODE.get(self.redirect_path)
        else:
            redirect_uri = redirect_uri or self.redirect_uri

        return self.env.user.create_access_token(
            scope=scope, audience=self.client_id, redirect_uri=redirect_uri
        )

    def validate_token(self, token):
        client = self
        if not client:
            payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": True,
                    "verify_aud": False,
                    "verify_iss": False,
                }
            )
            client = self.sudo().search([('client_id', '=', payload.get('aud'))], limit=1)
        audience = client and client.client_id
        return self.env['amr.token'].validate(token, audience=audience)

    def validate_refresh_token(self, token):
        # client = self
        # if not client:
        #     payload = jwt.decode(
        #         token,
        #         options={
        #             "verify_signature": False,
        #             "verify_exp": True,
        #             "verify_aud": False,
        #             "verify_iss": False,
        #         }
        #     )
        #     client = self.sudo().search([('client_id', '=', payload.get('aud'))], limit=1)
        # audience = client and client.client_id
        return self.env['oidc.refresh.token'].validate_token(token, self.client_id)

    # def validate(self, token, refresh_token=False):
    #     client = self
    #     if not client:
    #         payload = jwt.decode(
    #             token,
    #             options={
    #                 "verify_signature": False,
    #                 "verify_exp": True,
    #                 "verify_aud": False,
    #                 "verify_iss": False,
    #             }
    #         )
    #         client = self.sudo().search([('client_id', '=', payload.get('aud'))], limit=1)
    #     audience = client and client.client_id
    #     return self.env['amr.token'].validate(token, refresh_token=refresh_token, audience=audience)
