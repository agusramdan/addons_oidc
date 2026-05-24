# -*- coding: utf-8 -*-

from werkzeug.exceptions import Unauthorized
from odoo import api, models
from odoo.http import request
from odoo.service import security


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def set_session(cls, user, session_token=None):
        session = request.session
        session.rotate = True
        session.uid = user.id
        session.login = user.login
        if user:
            session.session_token = security.compute_session_token(session, request.env)
        else:
            session.session_token = session_token
        #v16 handle session berbeda dengan 16
        # if not session.session_token:
        #     request.update_env()
        #     session.uid = None
        #     session.login = None
        # else:
        #     request.update_env(user=request.session.uid)

        # v13 handle session berbeda dengan 16
        if not session.session_token:
            request.uid = None
            session.uid = None
            session.login = None
        else:
            request.uid = user.id
            request.disable_db = False
            session.get_context()

    @classmethod
    def _auth_method_auto_login(cls):
        # Menggunakan token oidc untuk handle API call
        heleper = request.env['amr.resource.helper'].sudo()
        token=heleper.get_param_token()
        # VALIDASI TOKEN
        validate = heleper.get_validate_user(token)
        if not validate:
            raise Unauthorized('Invalid Token')

        user = heleper.get_user_match(validate)

        if not user:
            raise Unauthorized('User not found')

        if request.uid != user.id:
            cls.set_session(user)
