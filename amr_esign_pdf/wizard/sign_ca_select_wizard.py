# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class UserCaDataWizard(models.TransientModel):
    _name = 'sign.ca.select.wizard'
    _description = 'User CA Selection Wizard'

    pdf_sign_id = fields.Many2one('pdf.sign', string='sign', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    user_ca_id = fields.Many2one('user.ca.data', 'User CA', required=True, domain="[('user_id', '=', user_id)]")
    password = fields.Char()
    signature_pdf = fields.Binary(string="Signature Pdf")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        user_ca_id = None
        if res.get('user_id'):
            user_ca_id = self.user_ca_id.search(
                [('auto_signature', '=', True), ('user_id', '=', res.get('user_id'))],
                limit=1
            )
        if user_ca_id:
            res['user_ca_id'] = user_ca_id.id
        # if self.user_ca_id.env.user.has_group('base.group_system'):
        #     res['is_admin'] = True
        return res

    def action_sign_pdf(self):
        self.ensure_one()
        try:
            self.user_ca_id.load_signer_from_ca_data(
                dry_run=True, password=self.password or None
            )
        except Exception as e:
            raise UserError(str(e))
        self.pdf_sign_id.sign_pdf_using(
            self.user_ca_id, password=self.password or None, signature_pdf=self.signature_pdf
        )
        return {'type': 'ir.actions.act_window_close'}
