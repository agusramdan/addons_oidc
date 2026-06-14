# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)


class ServiceEndpointMixin(models.AbstractModel):
    _name = "service.endpoint.mixin"

    # code = fields.Char()
    base_url = fields.Char(compute='_compute_base_url')
    base_url_value = fields.Char()
    config_param_name = fields.Char()
    base_path = fields.Char(help="/api/v1")
    audience = fields.Char()
    credential_id = fields.Many2one("service.credential")
    timeout = fields.Integer(default=30, )
    active = fields.Boolean(default=True, )

    def open_config_parameter(self):
        param = self.env['ir.config_parameter'].sudo().search(
            [('key', '=', self.config_param_name)],
            limit=1
        ) or self.env['ir.config_parameter'].sudo().create({'key': self.config_param_name, 'value': ""})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.config_parameter',
            'res_id': param.id,
            'view_mode': 'form',
        }

    def get_value_config_param(self, config_param_name=None, value_without_config_param=None):
        config_param_name = config_param_name or self and self.config_param_name
        if config_param_name:
            return self.env['ir.config_parameter'].sudo().get_param(config_param_name) or None
        else:
            return value_without_config_param

    @api.depends('base_url_value', 'config_param_name')
    def _compute_base_url(self):
        for rec in self:
            if rec.config_param_name:
                url = rec.get_value_config_param(config_param_name=rec.config_param_name)
            else:
                url = rec.base_url_value
            if url:
                try:
                    parsed = urlparse(url)
                    rec.base_url = f"{parsed.scheme}://{parsed.netloc}"
                except:
                    rec.base_url = False
            else:
                rec.base_url = False

    def get_base_url(self):
        return (self.base_url or "").rstrip("/")

    def get_path_url(self):
        return (self.base_path or "").rstrip("/")

    def get_url(self, path=None):
        base_path = (self.base_path or "").rstrip("/")
        base_url = (self.base_url or "").rstrip("/")
        path = (path or "").rstrip("/")
        if not path and not base_path:
            return base_url

        if base_path:
            if path and not path.startswith('/'):
                path = f"{base_path}/{path}"
            elif not path:
                path = base_path

        _logger.info("path %s .",path)
        if path.startswith('/'):
            return f"{base_url}{path}"
        else:
            return f"{base_url}/{path}"

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
                "default_endpoint_model": self._name,
            }
        }


class ServiceEndpoint(models.Model):
    _name = "service.endpoint"
    _inherit = 'service.endpoint.mixin'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True, )
