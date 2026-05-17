# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oidc_token_issuer = fields.Char("Issuer", config_parameter='amr_token.oidc_issuer',)
    oidc_token_expires_in = fields.Integer("Expired in (sec)", config_parameter='amr_token.oidc_expires_in',)
    oidc_token_retention_in = fields.Integer("Retention in (sec)", config_parameter='amr_token.oidc_retention_in',)
    oidc_token_secret = fields.Char("Secret", config_parameter='amr_token.secret',)

    # module_amr_auth_oauth = fields.Boolean("Client OAuth")
    # module_amr_auto_login = fields.Boolean("Auto Login OAuth")

    # def create_jwt_token(self):
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Create Token',
    #         'view_mode': 'form',
    #         'res_model': 'antareja.create.token.wizard',
    #         # 'res_id': self.env.company.id,
    #         'target': 'current',
    #         # 'context': {
    #         #     'form_view_initial_mode': 'edit',
    #         # },
    #     }
