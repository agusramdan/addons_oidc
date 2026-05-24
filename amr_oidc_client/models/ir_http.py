# -*- coding: utf-8 -*-

from werkzeug.exceptions import Unauthorized
from odoo import models
from odoo.http import request
from odoo.service import security

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
        request.uid = None
        session.uid = None
        session.login = None
    else:
        request.uid = uid
        request.disable_db = False
        session.get_context()


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _auth_method_oidc(cls):
        auth = request.httprequest.headers.get('Authorization')
        if not auth:
            raise Unauthorized('Missing Authorization Header')

        parts = auth.split()

        if len(parts) != 2:
            raise Unauthorized('Invalid Parts')

        scheme, token = parts

        if scheme.lower() != 'bearer':
            raise Unauthorized('Invalid Auth Scheme')
        heleper = request.env['amr.resource.helper'].sudo()
        # VALIDASI TOKEN
        validate = heleper.get_validate_user(token)
        if not validate:
            raise Unauthorized('Invalid Token')

        user = heleper.get_user_match(validate)

        if not user:
            raise Unauthorized('User not found')
        if request.uid != user.id:
            set_session(user.login, user.id)
        # request.env = request.env(user=user)
        # request.uid = user.id
