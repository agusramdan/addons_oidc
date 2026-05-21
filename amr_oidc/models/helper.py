# -*- coding: utf-8 -*-

import logging
import jwt
import time
import base64

from datetime import datetime, timedelta

from jwt import InvalidTokenError
from odoo import _, api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)


class TokenHelper(models.AbstractModel):
    _inherit = 'amr.token.helper'
    # helper will call from Controller
    @api.model
    def get_bearer_token(self):
        auth = request.httprequest.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return None
        data = auth.split(" ", 1)
        return data[1] if len(data) >1 else None

    @api.model
    def get_basic_auth(self):
        auth = request.httprequest.headers.get('Authorization')
        if not auth:
            return None, None

        try:
            scheme, encoded = auth.split(' ', 1)
            if scheme.lower() != 'basic':
                return None, None

            decoded = base64.b64decode(encoded).decode('utf-8')
            return decoded.split(':', 1)
        except Exception:
            return None, None

    @api.model
    def openid_configuration(self):
        result = super().openid_configuration()
        issuer = self.get_issuer()
        result.update(
            {
                "authorization_endpoint": f"{issuer}/oidc/authorize",
                "userinfo_endpoint": f"{issuer}/oidc/userinfo",
                # "jwks_uri": f"{issuer}/oidc/jwks",
                "response_types_supported": [
                    "code",
                    "token",
                    "id_token",
                ],
                # "subject_types_supported": [
                #     "public"
                # ],
                # "id_token_signing_alg_values_supported": [
                #     "RS256"
                # ],
                "scopes_supported": [
                    "openid",
                    "profile",
                    "email",
                ],
                "token_endpoint_auth_methods_supported": [
                    "client_secret_post",
                    "client_secret_basic",
                ],
                "claims_supported": [
                    "uid",
                    "db",
                    "user_id",
                    "sub",
                    "name",
                    "email",
                ],
            }
        )
        return result

    def oidc_token(self, **kwargs):
        grant_type = kwargs.get('grant_type')

        if grant_type == 'refresh_token':
            return self.do_refresh_grant(kwargs.get('refresh_token'))

        if grant_type == 'trusted_token':
            return self.do_trusted_grant(kwargs.get('access_token'))

        return super().oidc_token(**kwargs)


    @api.model
    def do_refresh_grant(self, refresh_token=None):
        if not refresh_token:
            return {'status':400, 'error':"invalid_grant"}

        payload = self.env['oidc.refresh.token'].validate_token(refresh_token)

        if not payload or not payload.get('token'):
            return {'status':400, 'error':"invalid_grant",'error_description': "Invalid or expired token"}
        user = self.env['res.users'].sudo().get_user_by_username(payload['sub'])
        return self.generate_user_token(user,payload)

    @api.model
    def oidc_introspect(self, **kwargs):
        active = False
        user = None
        payload = {}
        token = kwargs.get('access_token') or kwargs.get('token') or self.get_header_token() or self.get_bearer_token()
        if token:
            payload = self.env['oidc.client'].validate_token(token)
            if payload and payload.get('uid'):
                uid = payload.get('uid')
                user = self.env['res.users'].sudo().browse(uid)
                active = user.exists()
        if active:
            data = dict(payload)
            data.update(
                active=True,
                uid=user.id,
                user_id=user.id,
                name=user.name,
                login=user.login,
            )
            return self.oidc_introspect_payload_response_enhance(data)
        else:
            return {'active': False, "error": "invalid_token"}

    @api.model
    def oidc_introspect_payload_response_enhance(self, data):
        data['db'] = self.env.cr.dbname
        return data

    @api.model
    def oidc_profile(self, **kwargs):
        active = False
        payload = None
        user = None
        token = kwargs.get('access_token') or kwargs.get('token') or self.get_header_token() or self.get_bearer_token()
        if token:
            payload = request.env['oidc.client'].validate_token(token)
            if payload and payload.get('uid'):
                uid = payload.get('uid')
                user = request.env['res.users'].sudo().browse(uid)
                active = user.exists()

        if active:
            data = dict(payload)
            data.update(
                uid=user.id,
                user_id=user.id,
                name=user.name,
                login=user.login,
                db=request.session.db,
            )
            if 'status' in data:
                data.pop('status')
            return data
        else:
            return {'status': 401, "error": "invalid_token", "error_description": "Invalid Token", }


