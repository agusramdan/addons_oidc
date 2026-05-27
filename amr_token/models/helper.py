# -*- coding: utf-8 -*-

import logging
import jwt
import time
import base64

from odoo import _, api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResourceAccessToken(models.AbstractModel):
    _inherit = 'amr.resource.helper'

    def encode(self, **kw):
        return self.env['amr.token.helper'].encode(**kw)

    def decode(self, token, **kw):
        return self.env['amr.token.helper'].validate(token, **kw)


class TokenHelper(models.AbstractModel):
    _name = 'amr.token.helper'
    _description = 'Token Helper call from Controller'

    # helper will call from Controller
    @api.model
    def get_header_token(self):
        return self.env['amr.resource.helper'].get_header_token()

    @api.model
    def get_bearer_token(self):
        return self.env['amr.resource.helper'].get_bearer_token()

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
    def get_signature_type(self):
        config_parameter = self.env['ir.config_parameter'].sudo()
        return config_parameter.get_param('amr_token.signature_type', 'secret')

    def get_signature_algorithm(self):
        config_parameter = self.env['ir.config_parameter'].sudo()
        if config_parameter.get_param('amr_token.signature_type') == 'public_key':
            return config_parameter.get_param('amr_token.public_key_algorithm') or "RS256"
        else:
            return config_parameter.get_param('amr_token.secret_algorithm') or "HS256"

    # def get_token_signing_alg(self):
    #     config_parameter = self.env['ir.config_parameter'].sudo()
    #     if config_parameter.get_param('amr_token.signature_type')=='public_key':
    #         return [config_parameter.get_param('amr_token.secret_algorithm') or "RS256"]
    #     else:
    #         return [config_parameter.get_param('amr_token.public_key_algorithm') or "HS256"]

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
        return self.env['amr.resource.helper'].get_issuer()

    @api.model
    def get_audience(self):
        return self.env['amr.resource.helper'].get_audience()

    @api.model
    def openid_configuration(self):
        issuer = self.get_issuer()
        return {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/oidc/authorize",
            "introspection_endpoint": f"{issuer}/oidc/introspect",
            "token_endpoint": f"{issuer}/oidc/token",
            "userinfo_endpoint": f"{issuer}/oidc/userinfo",
            "jwks_uri": f"{issuer}/.well-known/jwks.json",
            "response_types_supported": [
                "code",
                "token",
                "id_token",
            ],
            "subject_types_supported": [
                "public"
            ],
            "id_token_signing_alg_values_supported": [self.get_signature_algorithm()],
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

    @api.model
    def oidc_jwks(self):
        return {
            "keys": self.env["amr.public.key"].sudo().get_jwks()
        }

    def oidc_token(self, **kwargs):
        grant_type = kwargs.get('grant_type')

        if grant_type == 'password':
            return self.do_password_grant(kwargs)

        if grant_type == 'challenge_approval':
            return self.do_challenge_grant(kwargs)

        if grant_type == 'digital_signature':
            # server version
            return self.do_digital_signature_grant(kwargs)

        return {
            'status': 401, 'error': "unsupported_grant_type",
            "error_description": _("Grant Type % Not Support") % grant_type
        }

    @api.model
    def do_password_grant(self, data):
        try:
            username = data.pop('username')
            password = data.pop('password')
        except KeyError:
            return {'status': 401, 'error': "invalid_grant", 'error_description': 'Missing username or password'}

        user = self.env['res.users'].sudo().get_user_by_username(username)
        if not user:
            return {'status': 401, 'error': "invalid_grant", 'error_description': 'User Not Found'}
        try:
            user.with_user(user)._check_credentials(password)
        except Exception:
            _logger.exception("Error _check_credentials")
            return {'status': 401, 'error': "invalid_grant"}

        client_id = data.pop('client_id', None)
        client_secret = data.pop('client_secret', None)

        access_token, _, expires_in = self.generate_user_token(user, **data)
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': expires_in,
        }

    @api.model
    def do_challenge_grant(self, data):
        client_id = data.pop('client_id', None)
        client_secret = data.pop('client_secret', None)
        grant_type = data.pop('grant_type', None)
        audience = data.pop('audience', None) or data.pop('aud', None)
        scope = data.pop('scope', "challenge")
        data.update({
            'iss': self.get_issuer(),
            'aud': audience or self.get_audience(),
            'scope': scope
        })
        challenge, _ = self.generate_token_asymmetric(data)
        return {
            'challenge': challenge
        }

    @api.model
    def do_digital_signature_grant(self, data):
        client_id = data.pop('client_id', None)
        client_secret = data.pop('client_secret', None)
        grant_type = data.pop('grant_type', None)

        audience = data.pop('audience', None) or data.pop('aud', None)
        data.update({
            'iss': self.get_issuer(),
            'aud': audience or self.get_audience(),
        })
        digital_signature, _ = self.generate_token_asymmetric(data)
        return {
            'digital_signature': digital_signature
        }

    def generate_user_token(self, user, audience=None, expires_in=None, scope='', **kw):
        audience = audience or kw.pop('aud', None)
        payload = dict(kw)

        payload.update({
            'uid': user.id,
            'user_id': user.login,
            'sub': user.login,
            'email': user.email,
            'db': self.env.cr.dbname,
        })
        resource = kw.get('resource')
        if resource:
            payload['aud'] = resource
        expires_in = expires_in or self.get_expires_in()
        access_token, payload = self.generate_token(
            payload, audience=audience, expires_in=expires_in, scope=scope
        )
        return access_token, payload, expires_in

        # return {
        #     'access_token': access_token,
        #     'token_type': 'Bearer',
        #     'expires_in': expires_in,
        # }

    @api.model
    def oidc_introspect(self, **kwargs):
        active = False
        user = None
        payload = {}
        token = kwargs.get('access_token') or kwargs.get('token') or self.get_header_token() or self.get_bearer_token()
        if token:
            payload = self.validate(token)
            _logger.info("Payload %s", payload)
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

    def encode(self, algorithm=None, alg=None, issuer=None, iss=None, audience=None, aud=None, **kw):
        algorithm = alg or algorithm
        issuer = iss or issuer
        audience = aud or audience
        scope = kw.pop('scope', '')
        return self.generate_token(kw, algorithm=algorithm, issuer=issuer, audience=audience, scope=scope)

    def generate_token(self, payload, algorithm=None, issuer=None, expires_in=None, audience=None, scope=''):
        algorithm = algorithm or self.get_signature_algorithm()
        expires_in = expires_in or self.get_expires_in()
        expire = int(time.time()) + expires_in
        payload.update({
            'iss': issuer or self.get_issuer(),
            'aud': audience or self.get_audience(),
            'exp': expire,
            'scope': scope
        })
        if algorithm.startswith('HS'):
            _logger.warning("Token signed with HS algorithm, validating via introspection endpoint")
            return self.generate_token_secret(payload, algorithm)
        else:
            return self.generate_token_asymmetric(payload, algorithm)

    def generate_token_asymmetric(self, payload, algorithm="RS256"):
        jwt_key = self.env['amr.public.key'].sudo().search([('algorithm', '=', algorithm)])
        if not jwt_key:
            raise Exception("Private Key Not Set")
        return jwt_key.generate_token(payload), payload

    def generate_token_secret(self, payload, algorithm="HS256"):
        jwt_secret = self.get_secret()
        if not jwt_secret:
            raise Exception("JWT Secret not set")
        return jwt.encode(
            payload,
            jwt_secret,
            algorithm=algorithm
        ), payload

    def decode(self, token, *kw):
        return self.validate(token)

    def validate(self, token):
        header = jwt.get_unverified_header(token)
        algorithm = header.get('alg')
        if algorithm.startswith('HS'):
            _logger.warning("Token signed with HS algorithm, validating via introspection endpoint")
            return self.validate_secret(token, algorithm=algorithm)
        else:
            return self.validate_asymmetric(token, header.get('kid'), algorithm=algorithm)

    def validate_secret(self, token, algorithm="HS256"):
        jwt_secret = self.get_secret()
        if not jwt_secret:
            raise Exception("JWT Secret not set")
        issuer = self.get_issuer()
        return jwt.decode(token, jwt_secret, algorithms=[algorithm], issuer=issuer, options={"verify_aud": False})

    def validate_asymmetric(self, token, kid, algorithm="RS256"):
        jwt_key = self.env['amr.public.key'].sudo().search([('algorithm', '=', algorithm), ('kid', '=', kid)])
        if not jwt_key:
            raise Exception("Public Key Not Set")
        issuer = self.get_issuer()
        return jwt_key.validate_token(token, issuer=issuer, options={"verify_aud": False})
