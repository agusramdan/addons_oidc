# -*- coding: utf-8 -*-

from werkzeug.exceptions import Unauthorized
from odoo import api, models
from odoo.http import request
from odoo.service import security


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

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
