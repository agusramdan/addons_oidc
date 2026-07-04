# -*- coding: utf-8 -*-

import base64

from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo import fields, models
from odoo import api, fields, models


class PdfVerifyWizard(models.TransientModel):
    _name = "pdf.verify.wizard"
    _description = "PDF Signature Verification"

    pdf_document_id = fields.Many2one(
        'pdf.document', readonly=True
    )
    pdf_file = fields.Binary(
        required=True,
        attachment=False,
    )
    filename = fields.Char()
    state = fields.Selection([
        ("draft", "Draft"),
        ("verified", "Verified"),
        ("failed", "Failed"),
    ], default="draft")
    message = fields.Text(readonly=True)
    line_ids = fields.One2many(
        "pdf.verify.wizard.line",
        "wizard_id",
        readonly=True,
    )



    def action_verify(self):
        self.ensure_one()

        self.line_ids.unlink()

        pdf_bytes = base64.b64decode(self.pdf_file)
        result = self.pdf_document_id.verify(pdf_bytes)

        for sig in result.signatures:
            self.env["pdf.verify.wizard.line"].create({

                "wizard_id": self.id,

                "field_name": sig.field_name,

                "signer_name": sig.signer_name,

                "user_ca_id": sig.user_ca_id.id if sig.user_ca_id else False,

                "valid": sig.valid,

                "serial_number": sig.serial_number,

                "issuer": sig.issuer,

                "subject": sig.subject,

                "signing_time": sig.signing_time,

                "message": sig.message,

            })

        self.state = "verified" if result.valid else "failed"

        self.message = result.message

class PdfVerifyWizardLine(models.TransientModel):
    _name = "pdf.verify.wizard.line"
    _description = "PDF Verification Result"

    wizard_id = fields.Many2one(
        "pdf.verify.wizard",
        required=True,
        ondelete="cascade",
    )
    field_name = fields.Char()
    signer_name = fields.Char()
    user_ca_id = fields.Many2one(
        "user.ca.data",
        readonly=True,
    )
    valid = fields.Boolean()
    signing_time = fields.Datetime()
    serial_number = fields.Char()
    issuer = fields.Char()
    subject = fields.Char()
    message = fields.Char()
