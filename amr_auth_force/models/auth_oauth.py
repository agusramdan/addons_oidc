# -*- coding: utf-8 -*-

import os
import base64
import requests
import json
import logging

from odoo import models, fields, api
from odoo.exceptions import AccessDenied, UserError

_logger = logging.getLogger(__name__)


class AuthOAuthProvider(models.Model):
    _inherit = 'auth.oauth.provider'

    token_endpoint = fields.Char("Token URL")
    force_login =fields.Boolean()

    def action_get_openid_configuration(self):
        if not self.issuer_url:
            raise UserError("Issuer URL not set")
        openid_config = requests.get(f"{self.issuer_url}/.well-known/openid-configuration").json()
        self.token_endpoint = openid_config.get('token_endpoint') or self.token_endpoint
        self.auth_endpoint = openid_config.get('authorization_endpoint') or self.auth_endpoint
        self.validation_endpoint = openid_config.get('introspection_endpoint') or self.validation_endpoint
        self.data_endpoint = openid_config.get('userinfo_endpoint') or self.data_endpoint

    def auth_token_rpc(self, username,password):
        self.ensure_one()
        client_secret = self.get_client_secret()
        credentials = f'{self.client_id}:{client_secret}'
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        header = {'Authorization': f'Basic {encoded_credentials}'}
        param = {'grant_type': 'password','username':username,'password':password}
        res = requests.post(self.token_endpoint, headers=header, params=param)
        return res.json()
