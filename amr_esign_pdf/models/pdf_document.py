import base64
import hashlib

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PdfDocument(models.Model):
    _name = 'pdf.document'
    _description = 'PDF Document'
    _order = 'name'

    name = fields.Char(required=True)
    pdf_file = fields.Binary('PDF File')
    pdf_filename = fields.Char('PDF Filename')
    pdf_hash = fields.Char('PDF Hash', compute='_compute_pdf_hash', store=True, readonly=True)
    pdf_lock = fields.Binary('PDF Lock')
    signed_pdf = fields.Binary('Signed PDF')
    signed_pdf_filename = fields.Char('Signed PDF Filename')
    state = fields.Selection(
        [('draft', 'Draft'), ('request', 'Request'), ('signed', 'Signed')],
        default='draft',
        string='State',
    )

    signature_ids = fields.One2many('pdf.sign', 'pdf_document_id', string='Signatures')

    @api.depends('pdf_file')
    def _compute_pdf_hash(self):
        for record in self:
            if record.pdf_file:
                try:
                    raw_pdf = base64.b64decode(record.pdf_file)
                    record.pdf_hash = hashlib.sha256(raw_pdf).hexdigest()
                except Exception:
                    record.pdf_hash = False
            else:
                record.pdf_hash = False

    def action_prepare_signature(self):
        self.ensure_one()
        if not self.pdf_file:
            raise UserError(_('Upload PDF file before preparing for signature.'))
        self.pdf_lock = self._prepare_pdf_lock(self.pdf_file)
        self.state = 'request'
        return True

    def action_reset(self):
        self.write({
            'state': 'draft',
            'pdf_lock': False,
            'signed_pdf': False,
            'signed_pdf_filename': False,
        })
        return True

    def _prepare_pdf_lock(self, pdf_data):
        # Placeholder for preparing PDF with a signature placeholder.
        # For PAdES multiple signature flow, this should create a PDF with a
        # reserved /Contents buffer and proper signature dictionary.
        return pdf_data

    def action_sign_pdf(self):
        """
        Create final signed PDF when all `pdf.sign` records are in state 'signed'.
        Currently this will simply copy `pdf_lock` to `signed_pdf` as a placeholder.
        Real implementation should perform incremental update and embed CMS
        from each `pdf.sign.cms_data` into `/Contents` using pyHanko/pikepdf.
        """
        self.ensure_one()
        unsigned = self.signature_ids.filtered(lambda s: s.state != 'signed')
        if unsigned:
            raise UserError(_('Not all signatures are applied. Pending: %s') % (len(unsigned),))
        if not self.pdf_lock:
            raise UserError(_('No prepared PDF lock available.'))
        # Placeholder: simply set signed_pdf to pdf_lock. Replace with real
        # PAdES assembly using pyHanko to merge CMS blobs into the PDF.
        self.signed_pdf = self.pdf_lock
        self.signed_pdf_filename = self.pdf_filename or 'signed_document.pdf'
        self.state = 'signed'
        return True
