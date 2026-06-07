# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ServiceEndpointMixin(models.AbstractModel):
    _name = "service.endpoint.mixin"

    code = fields.Char()
    base_url = fields.Char()
    base_path = fields.Char(help="/api/v1")
    audience = fields.Char()
    credential_id = fields.Many2one("service.credential")
    timeout = fields.Integer(default=30, )
    active = fields.Boolean(default=True, )

    def get_url(self, path=None):
        base_path = (self.base_path or "").rstrip("/")
        base_url = (self.base_url or "").rstrip("/")
        if path:
            if path != '/':
                path = base_path
            elif not path.startswith('/'):
                path = f"{base_path}/{path}"
        else:
            path = base_url

        if path:
            if path.startswith('/'):
                return f"{base_url}{path}"
            else:
                return f"{base_url}/{path}"
        return base_url

    def action_test_connection(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Test Endpoint",
            "res_model": "service.endpoint.test.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_endpoint_id": self.id,
            }
        }


class ServiceEndpoint(models.Model):
    _name = "service.endpoint"
    _inherit = 'service.endpoint.mixin'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True, )
