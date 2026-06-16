# -*- coding: utf-8 -*-

import json
import logging

from odoo.http import Controller, Response, request, route

from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response
from odoo.http import request

_logger = logging.getLogger(__name__)


class ControllerToken(Controller):
    @classmethod
    def handle_exception(cls, ex):

        if isinstance(ex, HTTPException):
            raise ex

        return cls.json_response(
            {
                "success": False,
                "error": "general_error",
                "error_description": str(ex),
            },
            status=500,
        )

    def valid_response(self, status, data):
        return Response(
            status=status,
            content_type='application/json; charset=utf-8',
            response=json.dumps(data),
        )

    def invalid_response(self, status, error, info=""):
        return self.make_response(status=status, error=error, error_description=info)

    def make_response(self, status=200, **payload):
        return Response(
            response=json.dumps(
                payload
                or {"error": "unknown_error", "error_description": "An unknown error occurred."}
            ),
            status=status,
            headers=[("Content-Type", "application/json")],
        )

    @route('/.well-known/openid-configuration', type='http', auth='public', methods=['GET'], csrf=False)
    def well_known_openid_configuration(self):
        payload = request.env['amr.token.helper'].openid_configuration()
        return self.make_response(**payload)

    @route("/.well-known/jwks.json", type='http', auth='public', methods=['GET'], csrf=False)
    def well_known_jwks(self):
        payload = request.env['amr.token.helper'].oidc_jwks()
        return self.make_response(**payload)

    @route('/oidc/token', type='http', auth='none', methods=['POST'], csrf=False)
    def api_oidc_token(self, **kwargs):
        try:
            payload = request.env['amr.token.helper'].oidc_token(**kwargs)
        except Exception:
            _logger.exception("Error oidc_token")
            return self.invalid_response(401, "invalid_request")

        return self.make_response(**payload)

    @route('/oidc/introspect', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def api_oidc_introspect(self, **kwargs):
        return self.oidc_introspect(**kwargs)

    def oidc_introspect(self, **kwargs):
        try:
            data = request.env['amr.token.helper'].oidc_introspect(**kwargs)
        except Exception:
            _logger.exception("Error oidc_introspect")
            return self.invalid_response(401, "invalid_token")

        active = data.get('active')
        if active:
            return self.make_response(**data)
        else:
            return self.make_response(401, **data)

    @route(['/oidc/profile', '/oidc/userinfo'], type='http', auth='none', methods=['GET'], csrf=False)
    def api_oidc_profile(self, **kwargs):
        try:
            payload = request.env['amr.token.helper'].oidc_profile(**kwargs)
        except Exception:
            _logger.exception("Error oidc_introspect")
            return self.invalid_response(401, "invalid_token")
        return self.make_response(**payload)
