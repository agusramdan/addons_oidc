# -*- coding: utf-8 -*-

import logging
import jwt
import requests


from jwt import PyJWKClient, InvalidTokenError
from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResourceAccessToken(models.AbstractModel):
    _inherit = 'amr.resource.helper'


    # @api.model
    # def get_audience(self):
    #     config_param = self.env['ir.config_parameter'].sudo()
    #     amr_resource_audience = config_param.get_param('amr_resource.audience', 'web.base.url')
    #     return config_param.get_param(amr_resource_audience) or config_param.get_param('web.base.url')
    #
    # @api.model
    # def get_audiences(self):
    #     return [self.get_audience()]
    #
    # @api.model
    # def get_oidc_config(self, issuer):
    #     url = issuer.rstrip('/') + '/.well-known/openid-configuration'
    #     response = requests.get(url)
    #     response.raise_for_status()
    #     return response.json()
    #
    # @api.model
    # def get_jwks_data(self, issuer):
    #     url = issuer.rstrip('/') + '/.well-known/jwks.json'
    #     response = requests.get(url)
    #     response.raise_for_status()
    #     return response.json()
    #
    # def generate_token(self, client_id=None, client_secret=None, **kw):
    #     issuer_url = kw.pop('iss', None) or kw.pop('issuer', None) or kw.pop('issuer_url', None)
    #     if not issuer_url:
    #         raise ValueError('Issuer (iss) is required')
    #     oidc_config = self.get_oidc_config(issuer_url)
    #     token_endpoint = oidc_config.get('token_endpoint')
    #     if client_id and client_secret:
    #         auth = (client_id, client_secret)
    #     else:
    #         auth = None
    #     response = requests.post(token_endpoint, data=kw, auth=auth)
    #     response.raise_for_status()
    #     return response.json()

    # @api.model
    # def introspect_token(self, token, client_id=None, client_secret=None, url=None, iss=None, **kw):
    #     if not url:
    #         if not iss:
    #             payload = jwt.decode(token, options={"verify_signature": False})
    #             iss = payload.get('iss')
    #         oidc_config = self.get_oidc_config(iss)
    #         url = oidc_config.get('introspection_endpoint')
    #
    #     if not url:
    #         raise ValueError('Introspection endpoint URL is required')
    #
    #     if client_id and client_secret:
    #         auth = (client_id, client_secret)
    #     else:
    #         auth = None
    #     # response = requests.get(url, param={'access_token': token}, auth=auth)
    #     response = requests.get(url, data={'access_token': token}, auth=auth)
    #     response.raise_for_status()
    #     return response.json()
    #
    # def validate_hs(self, token, **kw):
    #     result = self.introspect_token(token, **kw)
    #     if not result.get('active'):
    #         raise InvalidTokenError('Token is not active')
    #     return result

    # helper will call from Controller
    def validate(self, token):
        try:
            return self.env['auth.jwt.validator'].decode(token)
        except Exception as e:
            return super().validate( token)

    def get_uid(self, payload):
        uid = self.env['auth.jwt.validator']._get_uid(payload)
        if not uid:
            return super().get_uid(payload)

