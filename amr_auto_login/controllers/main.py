# -*- coding: utf-8 -*-

import base64
import logging
import json
import werkzeug

from werkzeug import url_encode

from odoo import fields, http
from odoo.http import request
from odoo.service import security

_logger = logging.getLogger(__name__)


# v16 handle session berbeda dengan 13
def set_session(login, uid, session_token=None):
    session = request.session
    session.rotate = True
    session.uid = uid
    session.login = login
    if login or uid:
        session.session_token = security.compute_session_token(session, request.env)
    else:
        session.session_token = session_token

    if not session.session_token:
        request.update_env()
        session.uid = None
        session.login = None
    else:
        request.update_env(user=request.session.uid)

# v13 handle session berbeda dengan 16
# def set_session(login, uid, session_token=None):
#     session = request.session
#     session.rotate = True
#     session.uid = uid
#     session.login = login
#     if login or uid:
#         session.session_token = security.compute_session_token(session, request.env)
#     else:
#         session.session_token = session_token
#     if not session.session_token:
#         request.uid = None
#         session.uid = None
#         session.login = None
#     else:
#         request.uid = uid
#         request.disable_db = False
#         session.get_context()


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
    return werkzeug.wrappers.Response(
        status=status,
        content_type='application/json; charset=utf-8',
        response=json.dumps(data),
    )


class ControllerAccess(http.Controller):

    @http.route(['/web_token_access'], type='http', auth='none', methods=['GET'], csrf=False)
    def web_token_access(self, token_access=None, redirect=None, **kw):

        token_data = request.env['trust.audience'].validate(token_access)
        if token_data and token_data.get('have_internal_user'):
            uid = token_data['uid']
            login = token_data.get('username') or token_data.get('sub')
            set_session(login, uid)

        # if not request.session.uid:
        #     _logger.info("Sudah login")
        # else:

        if redirect:
            url = redirect
        elif kw:
            url = "/web#%s" % url_encode(kw)
        else:
            url = "/web"
        return werkzeug.utils.redirect(url)
