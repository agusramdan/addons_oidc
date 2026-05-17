# -*- coding: utf-8 -*-

import logging
import json
import base64

from urllib.parse import urlencode

import werkzeug
from odoo import http, fields
from odoo.http import request
from werkzeug import url_encode
from ..tools.utils import get_bearer_token, valid_response, invalid_response

_logger = logging.getLogger(__name__)


# def _password_grant(data):
#     user = request.env['res.users'].sudo().search([
#         ('login', '=', data.get('username'))
#     ], limit=1)
#
#     if not user:
#         return invalid_response(401, "invalid_grant")
#     try:
#         user.with_user(user)._check_credentials(data.get('password'))
#     except Exception:
#         return invalid_response(401, "invalid_grant")
#
#     kw = request.env["amr.token"].login(user.id)
#     return valid_response(200, kw)


def get_header_token(self):
    return request.httprequest.headers.get("access_token") or request.httprequest.headers.get("token")


class ControllerOIDC(http.Controller):

    @http.route('/.well-known/openid-configuration', type='http', auth='public', methods=['GET'], csrf=False, )
    def well_known_openid_configuration(self):
        return self.openid_configuration()

    def openid_configuration(self):

        issuer = request.env['amr.token'].get_issuer()
        return valid_response(200, {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/oidc/authorize",
            "introspection_endpoint": f"{issuer}/oidc/introspect",
            "token_endpoint": f"{issuer}/oidc/token",
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
        })

    @http.route('/oidc/authorize', type='http', auth='public', csrf=False)
    def authorize(self, **params):
        user = request.env.user
        # params -> json -> base 64
        params_json = json.dumps(params)

        base64params = base64.urlsafe_b64encode(
            params_json.encode()
        ).decode()

        # belum login
        if user._is_public():
            return werkzeug.utils.redirect('/oidc/login_form?params=%s' % base64params)

        # tampilkan chooser
        values = {
            'user': user,
            'params': base64params,
        }

        return request.render('amr_oidc.custom_oidc_continue_template', values)

    @http.route('/oidc/login_form', type='http', auth='public', website=True, methods=['GET'], )
    def login_page(self, params=None):

        return request.render(
            'amr_oidc.custom_login_template',
            {'params': params}
        )

    @http.route('/oidc/authorize_continue', type='http', auth='user', csrf=False)
    def authorize_continue(self, params=None):
        kwargs = json.loads(
            base64.urlsafe_b64decode(
                params.encode()
            ).decode()
        )
        return self.oidc_authorize(**kwargs)

    @http.route(
        '/oidc/login/submit',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def login_submit(self, login=None, password=None, params=None):

        db = request.session.db

        try:

            uid = request.session.authenticate(
                db,
                login,
                password
            )

        except Exception:
            uid = False

        if not uid:
            return request.render(
                'amr_oidc.custom_login_template',
                {
                    'error': 'Invalid login/password',
                    'params': params
                }
            )
        kwargs = json.loads(
            base64.urlsafe_b64decode(
                params.encode()
            ).decode()
        )
        return self.oidc_authorize(**kwargs)

    def is_invalip_parameter_authorize(self, **params):
        client_id = params.get('client_id')
        redirect_uri = params.get('redirect_uri')
        response_type = params.get('response_type')
        client = request.env['oidc.client'].search([('client_id', '=', client_id), ], limit=1)
        if not client:
            return invalid_response(400, 'invalid_client')

        if not redirect_uri and client.redirect_uri:
            redirect_uri = client.redirect_uri

        if not client.validate_redirect_uri(redirect_uri):
            return invalid_response(400, 'invalid_redirect_uri')

        if response_type not in ['code', 'token']:
            return invalid_response(400, 'unsupported_response_type')

        return False

    def oidc_authorize(self, **params):

        invalid = self.is_invalip_parameter_authorize(**params)
        if invalid:
            return invalid

        client_id = params.get('client_id')
        redirect_uri = params.get('redirect_uri')
        response_type = params.get('response_type')
        scope = params.get('scope')
        state = params.get('state')

        client = request.env['oidc.client'].search([('client_id', '=', client_id), ], limit=1)
        if not client:
            return invalid_response(400, 'invalid_client')

        if not redirect_uri and client.redirect_uri:
            redirect_uri = client.redirect_uri

        if not client.validate_redirect_uri(redirect_uri):
            return invalid_response(400, 'invalid_redirect_uri')

        # hanya support authorization code flow
        if response_type == 'code':
            authorization_code = client.create_authorization_code(redirect_uri=redirect_uri, scope=scope)
            query = {
                'code': authorization_code.code
            }
            if state:
                query['state'] = state

            redirect_url = (
                f'{redirect_uri}?{urlencode(query)}'
            )

        elif response_type == 'token':
            access_token = client.create_access_token(scope=scope, )
            fragment = {
                'access_token': access_token.token,
                'token_type': 'Bearer',
                'expires_in': access_token.get_expires_in(),
            }

            if state:
                fragment['state'] = state

            redirect_url = (
                f'{redirect_uri}'
                f'#{urlencode(fragment)}'
            )
        else:
            return invalid_response(400, 'unsupported_response_type')

        return werkzeug.utils.redirect(redirect_url)

    @http.route('/oidc/token', type='http', auth='none', methods=['POST'], csrf=False)
    def api_token(self, **kwargs):
        return self.oidc_token(**kwargs)

    def oidc_token(self, **kwargs):
        grant_type = kwargs.get('grant_type')

        if grant_type == 'password':
            return self.do_password_grant(kwargs)

        if grant_type == 'refresh_token':
            return self.do_refresh_grant(kwargs.get('refresh_token'))

        if grant_type == 'trusted_token':
            return self.do_trusted_grant(kwargs.get('access_token'))

        return invalid_response(401, "unsupported_grant_type")

    @http.route(['/oidc/profile', '/oidc/userinfo'], type='http', auth='none', methods=['GET'], csrf=False)
    def api_oidc_profile(self, **kwargs):
        return self.oidc_profile(**kwargs)

    def oidc_profile(self, **kwargs):
        active = False
        token = kwargs.get('access_token') or kwargs.get('token') or get_header_token() or get_bearer_token()
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
            return valid_response(200, data)
        else:
            return invalid_response(401, "invalid_token", "Invalid Token")

    @http.route('/oidc/introspect', type='http', auth='none', methods=['GET'], csrf=False)
    def api_oidc_introspect(self, **kwargs):
        return self.oidc_introspect(**kwargs)

    def oidc_introspect_payload_response_enhance(self, data):
        data['db'] = request.session.db
        return data

    def oidc_introspect(self, **kwargs):
        active = False
        token = kwargs.get('access_token') or kwargs.get('token') or get_header_token() or get_bearer_token()
        if token:
            payload = request.env['oidc.client'].validate_token(token)
            if payload and payload.get('uid'):
                uid = payload.get('uid')
                user = request.env['res.users'].sudo().browse(uid)
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
            return valid_response(200, self.oidc_introspect_payload_response_enhance(data))
        else:
            return valid_response(401, {'active': False, "error": "invalid_token"})

    def do_password_grant(self, data):
        user = request.env['res.users'].sudo().search([
            ('login', '=', data.get('username'))
        ], limit=1)

        if not user:
            return invalid_response(401, "invalid_grant")
        try:
            user.with_user(user)._check_credentials(data.get('password'))
        except Exception:
            return invalid_response(401, "invalid_grant")

        kw = request.env["amr.token"].login(user.id)
        return valid_response(200, kw)

    def do_trusted_grant(self, token_access):
        return invalid_response(401, "invalid_grant")
        # payload = self.env['amr.token.audience'].validate(token_access)
        # if payload and payload.get('uid'):
        #     kw = request.env["amr.token"].login(payload['uid'])
        #     return valid_response(200, kw)
        # else:
        #     return invalid_response(401, "invalid_grant")

    def do_refresh_grant(self, refresh_token=None):
        if not refresh_token:
            return invalid_response(200, "invalid_request")

        payload = request.env['oidc.refresh.token'].validate_token(refresh_token)

        if not payload or not payload.get('token'):
            return invalid_response(400, "invalid_grant", "Invalid or expired token")

        # revoke old token
        kw = request.env["amr.token"].login(payload['user_id'])
        return valid_response(200, kw)
