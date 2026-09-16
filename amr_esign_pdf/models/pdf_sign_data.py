# -*- coding: utf-8 -*-

import json

from odoo import fields, models


class PdfSignData(models.TransientModel):
    _name = "pdf.sign.data"
    _description = "PDF Sign Render Data"

    template_id = fields.Many2one("pdf.sign.template",readonly=True,)
    data_json = fields.Text(readonly=True,)

    def get_data(self):
        self.ensure_one()

        try:
            return json.loads(self.data_json or "{}")
        except (TypeError, ValueError):
            return {}

    def get_value(self, path, default=None):
        self.ensure_one()

        value = self.get_data()

        for key in path.split("."):
            if not isinstance(value, dict):
                return default

            value = value.get(key)

            if value is None:
                return default

        return value
