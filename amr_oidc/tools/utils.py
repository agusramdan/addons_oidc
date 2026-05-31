# -*- coding: utf-8 -*-

import base64
import json
import logging

from werkzeug.wrappers import Response

from odoo.http import request

_logger = logging.getLogger(__name__)


def get_bearer_token():
    auth = request.httprequest.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    return auth.split(" ", 1)[1]


def get_basic_auth():
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


def valid_response(status, data):
    return Response(
        status=status,
        content_type='application/json; charset=utf-8',
        response=json.dumps(data),
    )


def invalid_response(status, error, info=""):
    return Response(
        status=status,
        content_type='application/json; charset=utf-8',
        response=json.dumps({
            'error': error,
            'error_description': info,
        }),
    )


def make_response_error(status=400, error="", error_description=""):
    return Response(
        json.dumps({"error": error, 'error_description': error_description}),
        status=status,
        headers=[("Content-Type", "application/json")]
    )
