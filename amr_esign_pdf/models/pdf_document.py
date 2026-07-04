# -*- coding: utf-8 -*-

import base64
import hashlib
import logging
from io import BytesIO

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.fields import enumerate_sig_fields
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers as ph_signers
from pyhanko.sign.signers import PdfSignatureMetadata
from pyhanko.sign.signers.cms_embedder import SigAppearanceSetup
from pyhanko.sign.fields import SigFieldSpec, append_signature_field
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.Logger(__name__)


class PdfDocument(models.Model):
    _name = 'pdf.document'
    _inherit = ['deep.link.mixin']
    _description = 'PDF Document'
    _order = 'name'

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company
    )
    user_id = fields.Many2one(
        'res.users', string='Maker', default=lambda self: self.env.user
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('request', 'Request'), ('signed', 'Signed'),
         ('rejected', 'Rejected'), ('error', 'Error'), ('cancel', 'Cancel'), ],
        default='draft',
        string='State',
    )
    # | Tingkat | Istilah (Indonesia) | Istilah (Inggris) | Deskripsi                                                               |
    # | ------- | ------------------- | ----------------- | ----------------------------------------------------------------------- |
    # | 1       | Publik              | Public            | Dapat diakses siapa saja tanpa pembatasan.                              |
    # | 2       | Internal            | Internal Use Only | Hanya untuk pegawai atau pihak internal organisasi.                     |
    # | 3       | Rahasia Terbatas    | Confidential      | Informasi sensitif yang hanya boleh diakses oleh pihak yang berwenang.  |
    # | 4       | Rahasia             | Secret            | Jika bocor dapat menimbulkan kerugian yang signifikan bagi organisasi.  |
    # | 5       | Sangat Rahasia      | Top Secret        | Tingkat kerahasiaan tertinggi, hanya dapat diakses oleh orang tertentu. |

    confidentiality = fields.Selection([
        ('public', 'Public'),
        ('internal', 'Internal Use Only'),
        ('confidential', 'Confidential'),
        ('secret', 'Secret'),
        ('top_secret', 'Top Secret '),
    ], default='internal',
    )

    # | Use      | Istilah                  | Deskripsi                                                       | Contoh                                                                                        |
    # |----------| ------------------------ | --------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
    # | internal | **Internal Only**        | Hanya berlaku dan diakui di dalam organisasi.                   | Approval memo, persetujuan cuti, approval purchase request.                                   |
    # | partner  | **Partner Trusted**      | Diakui oleh organisasi yang memiliki perjanjian kerja sama.     | Kontrak B2B dengan partner tertentu.                                                          |
    # | public   | **Publicly Trusted**     | Diakui secara luas karena menggunakan CA publik yang dipercaya. | Kontrak dengan pelanggan, dokumen untuk pihak ketiga.                                         |

    signature_scope = fields.Selection([
        ("internal", "Internal"),
        ("partner", "Partner"),
        ("public", "Public"),
    ], default="internal")

    template_id = fields.Many2one('pdf.sign.template', string='Signature Templates')
    # source
    issuer = fields.Char(
        'Issuer',
        help="Server/Application document issuer"
    )
    source_sign = fields.Selection(
        [('independent', 'Independent'),
         ('sign_to_approve', 'Sign to Approve'),
         ('sign_from_approve', 'Sign from Approve'),
         ], default='independent', help="""
        Independent : Document Not related with other Model.
        Sign to Approve : Sign document will approve other model.
        Sign from Approve : Another model approval will propagate sign this document.
        """
    )
    source_application = fields.Char(
        help="Server/Application approval"
    )
    source_model = fields.Char()
    source_res_id = fields.Integer()

    pdf_file = fields.Binary('PDF File')
    pdf_filename = fields.Char('PDF Filename')
    pdf_hash = fields.Char('PDF Hash', readonly=True)

    pdf_lock_file = fields.Binary('Lock Lock', readonly=True)
    pdf_lock_filename = fields.Char('Lock Filename')
    pdf_lock_hash = fields.Char('Lock Hash', readonly=True)
    deep_link_hash = fields.Char('Deep Link Hash', readonly=True, related='pdf_lock_hash')

    pre_signed_pdf = fields.Binary('Pre Signed PDF', readonly=True)
    next_sign_pdf = fields.Many2one('pdf.sign', compute='_compute_next_sign_pdf')
    pre_signed_qr = fields.Char('Pre Signed QR', compute='_compute_next_sign_pdf')

    signed_pdf = fields.Binary('Signed PDF', readonly=True)
    signed_pdf_filename = fields.Char('Signed PDF Filename', readonly=True)

    signature_ids = fields.One2many('pdf.sign', 'pdf_document_id', string='Signatures')
    notes = fields.Text()
    error_message = fields.Text()

    @api.depends('state','signature_ids.state')
    def _compute_next_sign_pdf(self):
        for rec in self:
            next_sign_pdf = rec.get_next_sign_pdf()
            if next_sign_pdf:
                rec.next_sign_pdf = next_sign_pdf.id
                rec.pre_signed_qr = next_sign_pdf.deep_link
            else:
                rec.pre_signed_qr = ""
                rec.next_sign_pdf = False

    def get_signed_pdf_filename(self):
        self.ensure_one()
        return self.pdf_filename or '%s_signed.pdf' % (self.name or 'signed_document')

    def action_prepare_signature(self):
        self.ensure_one()
        self.validate_request_approval()
        self.event_approval_start()

    def validate_request_approval(self, **kwargs):
        self.ensure_one()
        if not self.pdf_file:
            raise UserError(_('Upload PDF file before preparing for signature.'))

        if not self.signature_ids:
            raise UserError(_('Add at least one signature line before signing.'))

    def event_approval_start(self, **kwargs):
        self.ensure_one()
        pdf_bytes = base64.b64decode(self.pdf_file)
        pdf_lock_bytes = self.signature_ids.prepare_signature_field_pdf(pdf_bytes)
        pdf_filename = self.get_signed_pdf_filename()
        self.signature_ids.write({
            'state': 'request',
        })
        self.write({
            'pre_signed_pdf': base64.b64encode(pdf_lock_bytes),
            'pdf_hash': hashlib.sha256(pdf_bytes).hexdigest(),
            'pdf_lock_hash': hashlib.sha256(pdf_lock_bytes).hexdigest(),
            'pdf_lock_file': base64.b64encode(pdf_lock_bytes),
            'pdf_lock_filename': pdf_filename,
            'state': 'request',
        })
        all_done = True
        for sign in self.signature_ids:
            if sign.state == 'request':
                if sign.auto_sign_after_request:
                    if not sign.user_id:
                        sign.user_id = sign.user_execution_id
                    user_ca = sign.get_auto_sign_ca()
                    user_ca and sign.sign_pdf_using(user_ca)
            elif sign.state != 'signed':
                all_done = False
        return all_done

    def action_reset(self):
        self.write({
            'state': 'draft',
            'pre_signed_pdf': False,
            'pdf_lock_hash': False,
            'pdf_lock_file': False,
            'signed_pdf': False,
            'signed_pdf_filename': False,
        })
        self.signature_ids.write({
            'state': 'draft',
        })
        return True

    def action_sign_all_pdf(self):
        self.ensure_one()
        if self.state != 'request':
            raise UserError(_('Invalid state for sign.'))
        if not self.pdf_lock_file:
            raise UserError(_('Prepare PDF file before signing.'))
        if not self.signature_ids:
            raise UserError(_('Add at least one signature line before signing.'))

        if all(t.get_auto_sign_ca().auto_signature for t in self.signature_ids if t.state == 'request'):
            for sign in self.signature_ids:
                if sign.state == 'request':
                    user_ca = sign.get_auto_sign_ca()
                    user_ca and sign.sign_pdf_using(user_ca)
            # pdf_bytes = base64.b64decode(self.pre_signed_pdf)
            # signed_pdf = self.signature_ids.sign_pdf(pdf_bytes)
            # self.set_signed_pdf(signed_pdf)
        else:
            # Can not auto signature.
            rec = self.get_next_sign_pdf()
            if rec.state == 'request':
                return rec.action_open_sign_wizard()
            # self.set_signed_pdf(self.pre_signed_pdf)
        return True

    def action_sign_pdf(self):
        sign = self.get_next_sign_pdf()
        if sign.state == 'request':
            return sign.action_open_sign_wizard()
        raise UserError("Sign PDF not found")

    def get_next_sign_pdf(self):
        for sign in self.signature_ids:
            if sign.state == 'request':
                return sign
        return self.signature_ids.browse()

    def set_signed_pdf(self, signed_pdf):
        _logger.info("call set_signed_pdf")
        self.ensure_one()
        pre_signed_pdf_b64encode = base64.b64encode(signed_pdf)
        if all(bool(t.state == 'signed') for t in self.signature_ids):
            pdf_filename = self.get_signed_pdf_filename()
            self.sudo().write({
                'pre_signed_pdf': pre_signed_pdf_b64encode,
                'signed_pdf': pre_signed_pdf_b64encode,
                'signed_pdf_filename': pdf_filename,
                'state': 'signed',
            })
        else:
            self.sudo().write({
                'pre_signed_pdf': pre_signed_pdf_b64encode,
            })
        return True

    # def action_open_sign_wizard(self):
    #     self.ensure_one()
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Select Certificate',
    #         'res_model': 'sign.ca.select.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_pdf_sign_id': self.id,
    #             'default_user_id': self.env.user.id,
    #             'user_ca_data_id': self.user_ca_data_id.id,
    #         }
    #     }

    def approval_by_pdf(self, pdf_binary: bytes):
        "Mengembalikan informasi signature field."
        reader = PdfFileReader(BytesIO(pdf_binary))
        fields = list(enumerate_sig_fields(reader))
        signatures = self.env['user.ca.data'].verify_signatures(fields)
        self.signature_ids.verify_approval(signatures)

    def action_download_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': (
                       '/web/content/?'
                       'model=%s&id=%s&field=%s&filename_field=%s&download=true'
                   ) % (
                       self._name,
                       self.id,
                       'signed_pdf',
                       'signed_pdf_filename',
                   ),
            'target': 'self',
        }

    def sign_from_approval(self, auto_sign_ca=False, **kwargs):
        user_execution = kwargs.pop('user_execution', None) or self.env.user
        user_ca = kwargs.pop('user_ca', None)
        # source_model = kwargs.get('source_model')
        # source_res_id = kwargs.get('source_res_id')
        sign = self.get_next_sign_pdf()
        if sign:
            sign = sign.sudo()
        else:
            raise UserError("Next sign pdf not found")
        sign.user_id = user_execution
        sign.user_execution_id = user_execution
        if user_ca:
            user_ca.load_signer_from_ca_data(dry_run=True)
        elif auto_sign_ca:
            user_ca = sign.get_auto_sign_ca()
        elif not user_ca:
            raise UserError("User CA not support.")

        sign.sign_pdf_using(user_ca, user_execution, **kwargs)

    def create_from_approval(self, **kwargs):
        signature_ids = kwargs.pop('signature_ids', [])
        signature_ids = self.signature_ids.safe_data_approval_task_line(signature_ids)
        prepare_create = self.safe_data_approval_task_line([kwargs])[0]
        prepare_create['signature_ids'] = signature_ids
        pdf_document = self.sudo().ensure_create_dict(prepare_create)
        pdf_document.action_prepare_signature()

        return pdf_document

    def cancel_from_approval(self, **kwargs):
        self.sudo().write({
            'state': 'cancel',
        })
        self.sudo().signature_ids.write({
            'state': 'cancel',
        })
