import base64
import hashlib
import fitz
from io import BytesIO

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PdfDocument(models.Model):
    _name = 'pdf.document'
    _description = 'PDF Document'
    _order = 'name'

    name = fields.Char(required=True)
    pdf_file = fields.Binary('PDF File')
    pdf_filename = fields.Char('PDF Filename')
    signed_pdf = fields.Binary('Signed PDF')
    signed_pdf_filename = fields.Char('Signed PDF Filename')
    state = fields.Selection(
        [('draft', 'Draft'), ('signed', 'Signed')],
        default='draft',
        string='State',
    )
    signature_ids = fields.One2many('pdf.sign', 'pdf_document_id', string='Signatures')

    def _run_async(self, coro):
        import asyncio
        import threading

        if threading.current_thread() is threading.main_thread():
            loop = asyncio.new_event_loop()
        else:
            if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
                loop = asyncio.WindowsSelectorEventLoopPolicy().new_event_loop()
            else:
                loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def action_sign_pdf(self):
        self.ensure_one()
        if not self.pdf_file:
            raise UserError(_('Upload PDF file before signing.'))
        if not self.signature_ids:
            raise UserError(_('Add at least one signature line before signing.'))

        try:
            from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
            from pyhanko.sign import signers as ph_signers
            from pyhanko.sign.fields import SigFieldSpec
            from pyhanko.sign.signers import PdfSignatureMetadata
            from pyhanko.stamp import QRStampStyle
        except ImportError:
            raise UserError(_('pyHanko is required to generate signed PDF.'))

        pdf_bytes = base64.b64decode(self.pdf_file)

        for sign in self.signature_ids:
            sig_name = sign.name or 'Signature_%d' % (sign.seq or 1)
            kwargs = {'sig_field_name': sig_name}
            rects = None
            placeholder = sign.placeholder
            if placeholder:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                for page_number, page in enumerate(doc):
                    rects = page.search_for(placeholder)
                    if rects:
                        rects = page.search_for(placeholder)
                        kwargs['on_page'] = page_number
                        rect = rects[0]
                        kwargs['box'] = (
                            rect.x0,
                            rect.y0,
                            rect.x0 + 180,
                            rect.y0 + 70,
                        )
                        break

            if not rects:
                if getattr(sign, 'on_page', False) is not False:
                    kwargs['on_page'] = sign.on_page - 1
                if getattr(sign, 'box', False):
                    coords = [c.strip() for c in str(sign.box).split(',') if c.strip()]
                    if len(coords) == 4:
                        try:
                            kwargs['box'] = tuple(float(c) for c in coords)
                        except ValueError:
                            pass

            field_spec = SigFieldSpec(**kwargs)
            signature_meta = PdfSignatureMetadata(field_name=sig_name, name=sig_name)
            signer = sign.get_signer()
            stamp_style = QRStampStyle(
                stamp_text="""
            Ditanda tangani secara digital

            %(signer)s
            Timestamp: %(ts)s
            Scan QR untuk verifikasi
            
            """
            )
            pdf_signer = ph_signers.PdfSigner(
                signature_meta=signature_meta,
                signer=signer,
                new_field_spec=field_spec,
                stamp_style=stamp_style,
            )

            output = BytesIO()
            # pdf_signer.sign_pdf(IncrementalPdfFileWriter(BytesIO(pdf_bytes)), output=output)
            self._run_async(pdf_signer.async_sign_pdf(
                IncrementalPdfFileWriter(BytesIO(pdf_bytes)),
                appearance_text_params={
                    "url": sign.deep_link,
                    "signer": sign.user_ca_data_id.name,
                },
                output=output))
            pdf_bytes = output.getvalue()

        self.signed_pdf = base64.b64encode(pdf_bytes)
        pdf_filename = getattr(self, 'pdf_filename', False) or '%s_signed.pdf' % (self.name or 'signed_document')
        self.signed_pdf_filename = pdf_filename
        self.state = 'signed'
        return True
