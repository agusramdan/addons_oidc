# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ServiceCredential(models.Model):
    _name = "service.credential"
    _description = "Credential"

    name = fields.Char(required=True)
    source = fields.Selection(
        [
            ("database", "Database"),
            ("file_path", "File Path"),
            ("env_json", "Environment JSON"),
            ("env_path", "Environment Path"),
            ("config_path", "Config Path"),
            ("system_parameter_json", "System Parameter JSON"),
            ("system_parameter_path", "System Parameter Path"),
        ],
        required=True,
    )
    reference = fields.Char()
    credential_json = fields.Text()

    def action_config_credential(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Config Credential",
            "res_model": "service.credential.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_endpoint_id": self.id,
            }
        }
