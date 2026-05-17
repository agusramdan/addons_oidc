# -*- coding: utf-8 -*-

import logging
import jwt
import time
import base64

from datetime import datetime, timedelta

from jwt import InvalidTokenError
from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)


class AccessToken(models.Model):
    _name = 'amr.token'
    active = fields.Boolean(default=True)
    token = fields.Char('Token', required=True)
    user_id = fields.Many2one('res.users', string='User')
    expires = fields.Integer('Expires (Epoc)')
    retention = fields.Integer('Retention (Epoc)')

    @api.model
    def get_expires_in(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('amr_token.expires_in')) or (60 * 60 * 24)

    @api.model
    def get_retention_in(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('amr_token.retention_in')) or (60 * 60 * 4)

    @api.model
    def get_secret(self):
        return self.env['ir.config_parameter'].sudo().get_param('amr_token.secret')

    @api.model
    def get_issuer(self):
        return self.env['ir.config_parameter'].sudo().get_param('amr_token.issuer') or self.env[
            'ir.config_parameter'].sudo().get_param('web.base.url')

    @api.model
    def get_audience(self):
        return self.env['ir.config_parameter'].sudo().get_param('database.uuid')

    @api.model
    def get_algorithm(self):
        return 'HS256'

    def login(self, uid):
        user = self.env["res.users"].sudo().browse(uid)
        expires_in = self.get_expires_in()
        access_token, payload = self.generate_token(user, expires_in=expires_in)
        refresh_token = self.create_refresh_token(user)
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': expires_in,
            "refresh_token": refresh_token
        }

    def create_refresh_token(self, user):
        Refresh = self.env["oidc.refresh.token"].sudo()

        token = Refresh.generate_token()
        expires_in = (60 * 60 * 24 * 14)
        expire = int(time.time()) + expires_in
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        Refresh.create({
            "token": token,
            "user_id": user.id,
            "expires_at": expires_at,
        })
        payload = {
            'token': token,
            'data': f"{user.id}-{user.email}-{time.time()}-{self.env.cr.dbname}",
            'aud': self.get_audience(),
            'iss': self.get_issuer(),
            'exp': expire
        }
        return jwt.encode(
            payload,
            self.get_secret(),
            algorithm=self.get_algorithm()
        )

    def generate_token(self, user, expires_in=None, audience=None, scope=''):
        jwt_secret = self.get_secret()
        if not jwt_secret:
            raise Exception("JWT Secret not set")
        expires_in = expires_in or self.get_expires_in()
        expire = int(time.time()) + expires_in
        payload = {
            'uid': user.id,
            'user_id': user.login,
            'sub': user.login,
            'email': user.email,
            'db': self.env.cr.dbname,
            'iss': self.get_issuer(),
            'aud': audience or self.get_audience(),
            'exp': expire,
            'scope': scope
        }
        return jwt.encode(
            payload,
            self.get_secret(),
            algorithm=self.get_algorithm()
        ), payload

    def validate(self, token, audience=None):
        try:
            payload = jwt.decode(
                token,
                self.get_secret(),
                issuer=self.get_issuer(),
                audience=audience or self.get_audience(),
                algorithms=[self.get_algorithm()],
                options={
                    "require": ["exp", "iss", "aud"]
                }
            )
            return payload
        # except InvalidIssuerError:
        #     pass
        # except InvalidAudienceError:
        #     pass
        # except ExpiredSignatureError:
        #     pass
        except InvalidTokenError:
            pass
        return None

    # def client_token_validation(self, token):
    #     return self.env['oidc.client'].client_auth(token)

    def create_access_token(self, user, retention_in=None, expires_in=None, scope='', audience=None):
        retention_in = retention_in or self.get_retention_in()
        token, payload = self.generate_token(user, scope=scope, audience=audience, expires_in=expires_in)
        vals = {
            'user_id': user.id,
            'token': token,
            'expires': int(payload['exp']),
            'retention': time.time() + retention_in,
        }
        access_token = self.sudo().create(vals)
        # we have to commit now
        # be called before we finish current transaction.
        self._cr.commit()
        return access_token

    def get_access_token(self, user=None, create=False):
        user = user or self.env.user
        epoch_time = time.time()
        access_token = self.sudo().search(
            [('user_id', '=', user.id), ('expires', '>', epoch_time)], order='expires DESC', limit=1
        ) or create and self.create_access_token(user)

        return access_token and access_token.token or None

    def cron_cleanup_tokens(self):
        epoch_time = time.time()
        tokens = self.sudo().search([('retention', '<', epoch_time)])
        tokens.sudo().unlink()
