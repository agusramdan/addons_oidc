
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PdfSign(models.Model):
    _name = 'pdf.sign'
    _description = 'PDF Sign'
    _order = 'seq, name'

    name = fields.Char(required=True)
    pdf_document_id = fields.Many2one('pdf.document', string='PDF Document', required=True)
    user_ca_data_id = fields.Many2one('user.ca.data', string='CA Data')
    seq = fields.Integer('Sequence')
    placeholder = fields.Char('Placeholder')
    on_page = fields.Integer('On Page')
    box = fields.Char('Box')
    deep_link = fields.Char('Deep Link')

    def get_signer(self):
        self.ensure_one()
        if not self.user_ca_data_id:
            raise ValidationError(_('No CA data associated with this signature.'))
        return self.user_ca_data_id.load_signer_from_ca_data()     
