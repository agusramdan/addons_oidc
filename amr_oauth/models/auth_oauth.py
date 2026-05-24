# -*- coding: utf-8 -*-

import os
import base64
import requests
import logging

from odoo import models, fields, api
from odoo.exceptions import AccessDenied


_logger = logging.getLogger(__name__)


class AuthOAuthProvider(models.Model):
    _inherit = 'auth.oauth.provider'

    issuer_url = fields.Char('Issuer', help='Issuer Name exp https://domain')
    user_template_id = fields.Many2one('res.users')
    user_signup = fields.Selection([
        ('none', 'Without Create user'),
        ('portal', 'Portal User'),
        ('internal', 'Internal User'),
        ('admin', 'Admin User'),
    ], string="User Signup")

    client_secret_env = fields.Char(
        'Client Secret Env Var',
        compute='_compute_client_secret_env',
        help='Environment variable name for OAuth Client Secret',
    )
    client_secret = fields.Char(
        'Client Secret',
        help='OAuth Client Secret for development or if not using environment variables.\n'
             'Not recommended for production.'
    )

    def _compute_client_secret_env(self):
        for res in self:
            res.client_secret_env = "CLIENT_SECRET_PROVIDER_%s" % res.id

    def get_client_secret(self):
        if self.client_secret_env:
            return os.getenv(self.client_secret_env)
        return self.client_secret

    def action_get_openid_configuration(self):
        openid_config = requests.get(f"{self.issuer_url}/.well-known/openid-configuration").json()
        self.auth_endpoint = openid_config.get('authorization_endpoint') or self.auth_endpoint
        self.validation_endpoint = openid_config.get('introspection_endpoint') or self.validation_endpoint
        self.data_endpoint = openid_config.get('userinfo_endpoint') or self.data_endpoint

    def auth_oauth_rpc(self, endpoint, access_token):
        self.ensure_one()
        client_secret = self.get_client_secret()
        if client_secret:
            credentials = f'{self.client_id}:{client_secret}'
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            header = {'Authorization': f'Basic {encoded_credentials}'}
        else:
            header = {'Authorization': f"Bearer {access_token}"}
        param = {'access_token': access_token}
        res = requests.get(endpoint, headers=header, params=param)
        return res.json()

    def auth_oauth_validate(self, access_token):
        """ return the validation data corresponding to the access token """
        validation = self.auth_oauth_rpc(self.validation_endpoint, access_token)
        if validation.get("error"):
            raise Exception(validation['error'])
        if self.data_endpoint:
            data = self.auth_oauth_rpc(self.data_endpoint, access_token)
            validation.update(data)
        # unify subject key, pop all possible and get most sensible. When this
        # is reworked, BC should be dropped and only the `sub` key should be
        # used (here, in _generate_signup_values, and in _auth_oauth_signin)
        email = validation.get('email')
        if not email:
            subject = next(filter(None, [
                validation.pop(key, None)
                for key in [
                    'sub',  # standard
                    'id',  # google v1 userinfo, facebook opengraph
                    'user_id',  # google tokeninfo, odoo (tokeninfo)
                ]
            ]), None)
            if not subject:
                raise AccessDenied('Missing subject identity')
        else:
            subject = email

        if self.user_signup == 'admin':
            if not email.startswith("admin-"):
                validation['email'] = f"admin-{email}"
                validation['user_id'] = f"admin-{subject}"
        else:
            validation['user_id'] = subject

        return validation

    def get_user_match(self, validation):
        email = validation.get('email')
        if email:
            return self.env['res.users'].search([('email', '=', email)], limit=1)
        return None

    def get_user_token_login(self, token):
        resource_helper = self.env['amr.resource.helper'].sudo()
        validate = resource_helper.validate(token)
        return self.get_user_match(validate)
