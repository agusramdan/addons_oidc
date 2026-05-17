# -*- coding: utf-8 -*-

import uuid
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    amr_token_secret = fields.Char("Secret", config_parameter='amr_token.secret',)
    amr_token_retention_in = fields.Integer("Retention in (sec)", config_parameter='amr_token.retention_in',)
    amr_token_expires_in = fields.Integer("Expired in (sec)", config_parameter='amr_token.expires_in',)
    amr_token_audience = fields.Char("Audience", config_parameter='database.uuid')

    module_amr_oidc = fields.Boolean("OIDC")
    module_amr_oauth = fields.Boolean("Client OAuth")
    module_amr_auto_login = fields.Boolean("Auto Login OAuth")

    def action_get_token_audience(self):
        database_uuid = str(uuid.uuid1())
        self.env['ir.config_parameter'].sudo().set_param('database.uuid', database_uuid)
