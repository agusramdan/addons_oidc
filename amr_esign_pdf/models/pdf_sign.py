from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PdfSign(models.Model):
    _name = 'pdf.sign'
    _description = 'PDF Sign'
    _order = 'name'

    name = fields.Char(required=True)
    pdf_document_id = fields.Many2one('pdf.document', string='PDF Document', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    signature_index = fields.Integer('Signature Index')
    cms_data = fields.Binary('CMS Data')
    state = fields.Selection(
        [('draft', 'Draft'), ('send', 'Send'), ('signed', 'Signed')],
        default='draft',
        string='State',
    )

    def action_send(self):
        self.ensure_one()
        if not self.pdf_document_id.pdf_lock:
            raise UserError(_('Prepare the PDF lock before sending the signature request.'))
        self.state = 'send'
        return True

    def action_apply_cms(self):
        self.ensure_one()
        if not self.cms_data:
            raise UserError(_('Upload CMS data before applying the signature.'))
        self.state = 'signed'
        self.pdf_document_id.signed_pdf = self.pdf_document_id.pdf_lock
        self.pdf_document_id.signed_pdf_filename = self.pdf_document_id.pdf_filename
        self.pdf_document_id.state = 'signed'
        return True
