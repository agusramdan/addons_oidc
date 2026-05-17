# -*- coding: utf-8 -*-

import logging
import json
import base64

from werkzeug.wrappers import Response

from odoo import api, http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class ControllerToken(http.Controller):

    @api.model
    def get_header_token(self):
        return request.httprequest.headers.get("access_token") or request.httprequest.headers.get("token")

    @api.model
    def get_bearer_token(self):
        auth = request.httprequest.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return None
        return auth.split(" ", 1)[1]

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
    def valid_response(self, status, data):
        return Response(
            status=status,
            content_type='application/json; charset=utf-8',
            response=json.dumps(data),
        )

    @api.model
    def invalid_response(self, status, error, info=""):
        return self.make_response(status=status, payload={"error": error, "error_description": info})

    @api.model
    def make_response(self, status=200, payload=None):
        return Response(
            response=json.dumps(payload or {"error": "unknown_error", "error_description": "An unknown error occurred."}),
            status=status,
            headers=[("Content-Type", "application/json")]
        )

    @http.route('/oidc/token', type='http', auth='none', methods=['POST'], csrf=False)
    def api_oidc_token(self, **kwargs):
        return self.oidc_token(**kwargs)

    def oidc_token(self, **kwargs):
        grant_type = kwargs.get('grant_type')

        if grant_type == 'password':
            return self.do_password_grant(kwargs)

        return self.invalid_response(401, "unsupported_grant_type")

    @api.model
    def do_password_grant(self, data):
        user = request.env['res.users'].sudo().search([
            ('login', '=', data.get('username'))
        ], limit=1)

        if not user:
            return self.invalid_response(401, "invalid_grant")
        try:
            user.with_user(user)._check_credentials(data.get('password'))
        except Exception:
            return self.invalid_response(401, "invalid_grant")

        kw = request.env["amr.token"].login(user.id)
        return self.make_response(200, kw)

    @http.route('/oidc/introspect', type='http', auth='none', methods=['GET'], csrf=False)
    def api_oidc_introspect(self, **kwargs):
        return self.oidc_introspect(**kwargs)

    def oidc_introspect(self, **kwargs):
        data = request.env['amr.token.helper'].oidc_introspect(**kwargs)
        active = data.get('active')
        if active:
            return self.make_response(200, data)
        else:
            return self.make_response(401, {'active': False, "error": "invalid_token"})
