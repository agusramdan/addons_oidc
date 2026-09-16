# -*- coding: utf-8 -*-

import json
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo import api, fields, models


class PdfSignPreviewWizard(models.TransientModel):
    _name = "pdf.sign.preview.wizard"
    _description = "PDF Sign QWeb Preview"

    template_id = fields.Many2one(
        "pdf.sign.template",
        string="Template",
        required=True,
        domain=[
            ("active", "=", True),
            ("renderer", "=", "qweb"),
        ],
    )

    data_json = fields.Text(
        string="Render Data",
        help="JSON data yang akan diberikan ke QWeb.",
    )

    pdf_file = fields.Binary(
        string="Generated PDF",
        readonly=True,
    )

    pdf_filename = fields.Char(
        readonly=True,
    )

    def action_generate(self):
        self.ensure_one()
        try:
            data = json.loads(self.data_json or "{}")
        except (TypeError, ValueError) as exc:
            raise UserError(
                _("Invalid JSON data:\n%s") % exc
            )

        pdf_bytes = self.template_id.generate_pdf_binary(
            render_data=data
        )

        self.write({
            "pdf_file": base64.b64encode(pdf_bytes),
            "pdf_filename": "%s.pdf" % self.template_id.name,
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }
