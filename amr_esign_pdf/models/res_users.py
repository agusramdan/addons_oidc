# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    user_ca_data_ids = fields.One2many('user.ca.data', 'user_id', string='CA')
    user_ca_data_default_id = fields.Many2one(
        'user.ca.data', string='CA Default Internal'
    )

    def ensure_have_user_ca_default(self):
        UserCaData = self.env['user.ca.data']

        for user in self:
            if user.user_ca_data_default_id:
                continue

            default_ca = UserCaData.search([
                ('user_id', '=', user.id),
                ('signature_scope', '=', 'internal'),
                ('auto_signature', '=', True),
            ], limit=1)

            if not default_ca:
                default_ca = self.env['user.ca.data'].create_self_signed_ca(
                    user, auto_signature=True, signature_scope='internal',name=user.name or "No Name"
                )
            user.user_ca_data_default_id = default_ca.id

        return True
