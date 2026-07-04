# -*- coding: utf-8 -*-

import base64
import json
import fitz
import logging
from io import BytesIO

from pyhanko.pdf_utils.content import RawContent
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.fields import enumerate_sig_fields
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.stamp import StaticStampStyle
from pyhanko.sign import signers as ph_signers
from pyhanko.sign.signers import PdfSignatureMetadata
from pyhanko.sign.signers.cms_embedder import SigAppearanceSetup
from pyhanko.sign.fields import SigFieldSpec, append_signature_field
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import io

from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.stamp import StaticStampStyle
_logger = logging.getLogger(__name__)

_original_apply = SigAppearanceSetup.apply


# hack here agar tampil di field
def _patched_apply(self, sig_annot, writer):
    # Jalankan implementasi asli
    _original_apply(self, sig_annot, writer)

    # Jika appearance dibuat, pastikan widget ikut di-update
    if sig_annot.container_ref and "/AP" in sig_annot:
        writer.mark_update(sig_annot.container_ref)
        # Opsional, untuk debugging
        # print("Widget marked for update:", sig_annot.container_ref)


SigAppearanceSetup.apply = _patched_apply


def get_signature_field(pdf_binary: bytes, field_name: str):
    """
    Mengembalikan informasi signature field.
    """
    reader = PdfFileReader(BytesIO(pdf_binary))

    for name, value, field_ref in enumerate_sig_fields(reader):
        if name == field_name:
            return {
                "exists": True,
                "signed": value is not None,
                "field_ref": field_ref,
                "value": value,
            }

    return {
        "exists": False,
        "signed": False,
        "field_ref": None,
        "value": None,
    }


def run_async(coro):
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


class PdfSign(models.Model):
    _name = 'pdf.sign'
    _inherit = ['deep.link.mixin']
    _description = 'PDF Sign'
    _order = 'pdf_document_id, seq, name'

    name = fields.Char(required=True)
    seq = fields.Integer('Sequence')
    state = fields.Selection(
        [('draft', 'Draft'), ('request', 'Request'), ('reject', 'Reject'),
         ('signed', 'Signed'), ('error', 'Error'), ('cancel', 'Cancel'), ],
        default='draft',
        string='State',
    )
    pdf_document_id = fields.Many2one(
        'pdf.document', string='PDF Document', required=True,
    )
    requester_id = fields.Many2one('res.users', related='pdf_document_id.user_id')
    pdf_lock_hash = fields.Char('Lock Hash', related='pdf_document_id.pdf_lock_hash')
    company_id = fields.Many2one(
        'res.company', related='pdf_document_id.company_id',
    )
    template_id = fields.Many2one(
        'pdf.sign.template',
        related='pdf_document_id.template_id',
        string='Signature Template'
    )
    email = fields.Char('Email')
    user_ca_data_id = fields.Many2one('user.ca.data', string='CA Data')
    user_id = fields.Many2one(
        'res.users', string='User'
    )
    user_execution_id = fields.Many2one(
        'res.users', 'User Execution',
        readonly=True,
        help="User who executed sign.",
    )
    date_execution = fields.Datetime('Date Execution', readonly=True, )
    # Signature Field
    signature_field = fields.Char(related='name')
    # Signature Field
    placeholder = fields.Char('Placeholder')
    width = fields.Float()
    height = fields.Float()

    # Box
    page_box = fields.Char('Page/Box')
    deep_link_hash = fields.Char(
        'Deep Link Hash', readonly=True, related='pdf_document_id.deep_link_hash'
    )
    source_model = fields.Char()
    source_res_id = fields.Integer()
    auto_sign_after_request = fields.Boolean()

    pre_signed_pdf = fields.Binary('Pre Signed PDF', readonly=True)
    pre_signed_pdf_filename = fields.Char('Signed PDF Filename', readonly=True)

    signed_pdf = fields.Binary('Signed PDF', readonly=True)
    signed_pdf_filename = fields.Char('Signed PDF Filename', readonly=True)

    @api.onchange('user_ca_data_id')
    def _onchange_user_ca_data_id(self):
        if self.user_ca_data_id.user_id:
            self.user_id = self.user_ca_data_id.user_id

    def get_signer(self, password=None):
        self.ensure_one()
        if not self.user_ca_data_id:
            raise ValidationError(_('No CA data associated with this signature.'))
        return self.user_ca_data_id.load_signer_from_ca_data(password=password)

    def get_appearance_text_params(self):
        sign = self.ensure_one()

        if sign.payload:
            try:
                appearance_text_params = json.loads(sign.payload) or {}
            except Exception as e:
                raise UserError(_(
                    'Invalid payload for signature field "%s". Please provide a valid JSON payload.'
                ) % sign.id) from e

        else:
            appearance_text_params = {}

        appearance_text_params.update(
            url=sign.deep_link,
            signer_name=sign.user_ca_data_id.name,
        )
        return appearance_text_params

    def prepare_signature_field_pdf(self, pdf_bytes):
        _logger.info("call prepare_signature_field_pdf")
        if not pdf_bytes or not self:
            return pdf_bytes
        # pdf_bytes = base64.b64decode(self.pdf_file)
        field_names = {}
        for sign in self:
            sig_name = sign.name
            signature_dict = get_signature_field(pdf_bytes, sig_name)
            if signature_dict["exists"]:
                continue
            field_names[sig_name] = sign

        # paceholder untuk signature field
        field_spec_list = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        # pdf_change = False
        for page_number, page in enumerate(doc):
            if not field_names:
                break
            # redaction_added = False
            next_break = True
            for sig_name, sign in list(field_names.items()):
                placeholder = sign.placeholder
                if not placeholder:
                    continue
                next_break = False
                rects = page.search_for(placeholder)
                if rects:
                    if len(rects) > 1:
                        _logger.warning(
                            "Placeholder %s ditemukan %d kali pada halaman %d",
                            placeholder,
                            len(rects),
                            page_number + 1,
                        )
                    rect = rects[0]
                    offset_x = self.template_id.offset_x
                    offset_y = self.template_id.offset_y
                    x0 = rect.x0 + offset_x
                    y0 = page.rect.height - rect.y1 + offset_y
                    x1 = x0 + (self.template_id.width or self.width or 180)
                    y1 = y0 + (self.template_id.height or self.height or 70)
                    field_spec_list.append(
                        SigFieldSpec(sig_field_name=sig_name, on_page=page_number, box=(x0, y0, x1, y1,))
                    )
                    field_names.pop(sig_name, None)
            if next_break:
                break
        doc.close()
        for sig_name, sign in field_names.items():
            kwargs = {'sig_field_name': sig_name}
            page_box = getattr(sign, 'page_box', "")
            if page_box:
                page, box = page_box.split('/')
                if page:
                    coords = [c.strip() for c in str(box).split(',') if c.strip()]
                    if len(coords) == 4:
                        try:
                            kwargs['on_page'] = int(page) - 1
                            kwargs['box'] = tuple(float(c) for c in coords)
                        except ValueError:
                            pass
                    elif len(coords) == 2:
                        try:
                            x0, y0 = tuple(float(c) for c in coords)
                            x1 = x0 + (sign.width or sign.template_id.width or 180)
                            y1 = y0 + (sign.height or sign.template_id.height or 70)
                            kwargs['on_page'] = int(page) - 1
                            kwargs['box'] = (x0, y0, x1, y1)
                        except ValueError:
                            pass
                    else:
                        _logger.info("kwargs else")
            _logger.info("kwargs set %s.", kwargs)
            field_spec_list.append(SigFieldSpec(**kwargs))

        output = BytesIO(pdf_bytes)
        writer = IncrementalPdfFileWriter(output)
        for field_spec in field_spec_list:
            append_signature_field(writer, field_spec)
        writer.write_in_place()
        pdf_bytes = output.getvalue()

        return pdf_bytes

    def sign_pdf(self, pdf_bytes, password=None, **kwargs):
        _logger.info("call sign_pdf")
        if not pdf_bytes or not self:
            return pdf_bytes

        for sign in self:
            pre_signed_pdf_base64 = base64.b64encode(pdf_bytes)
            sig_name = sign.name
            signature_dict = get_signature_field(pdf_bytes, sig_name)
            if not signature_dict["exists"]:
                raise UserError(_(
                    'Signature field "%s" does not exist in the PDF. Please prepare the signature fields first.'
                ) % sig_name)

            if signature_dict["signed"]:
                continue
            sign.state = 'request'

            signature_meta = PdfSignatureMetadata(field_name=sig_name, name=sig_name)
            signer = sign.get_signer(password=password)
            appearance_text_params = sign.get_appearance_text_params()
            signature_pdf_b64 = kwargs.get('signature_pdf')
            if signature_pdf_b64:
                stamp_style = sign.template_id.create_signature_stamp(signature_pdf_b64)
            else:
                stamp_style = sign.template_id.create_stamp_style(appearance_text_params)
            pdf_signer = ph_signers.PdfSigner(
                signature_meta=signature_meta,
                signer=signer,
                stamp_style=stamp_style,
            )
            output = BytesIO()
            run_async(pdf_signer.async_sign_pdf(
                IncrementalPdfFileWriter(BytesIO(pdf_bytes)),
                appearance_text_params=appearance_text_params,
                output=output))
            pdf_bytes = output.getvalue()
            signed_pdf_base64 = base64.b64encode(pdf_bytes)
            sign.sudo().write({
                'pre_signed_pdf_filename': f"[{sign.id}]pre_signed-{sign.pdf_document_id.pdf_filename}",
                'pre_signed_pdf': pre_signed_pdf_base64,
                'signed_pdf_filename': f"[{sign.id}]signed_pdf-{sign.pdf_document_id.pdf_filename}",
                'signed_pdf': signed_pdf_base64
            })
        self.sudo().write({'state': 'signed'})

        return pdf_bytes

    def set_signed(self, user_execution=None):
        _logger.info("call set_signed")
        if user_execution:
            if isinstance(user_execution, models.Model):
                user_execution_id = user_execution.id
            else:
                user_execution_id = int(user_execution)
        else:
            user_execution_id = self.env.user.id

        self.sudo().write({
            'user_execution_id': user_execution_id,
            'date_execution': fields.Datetime.now(),
            'state': 'signed',
        })

    def get_auto_sign_ca(self):
        self.user_id.sudo().ensure_have_user_ca_default()
        return self.user_id.user_ca_data_default_id

    def sign_pdf_using(self, user_ca, user_execution=None, **kwargs):
        _logger.info("call sign_pdf_using")
        sign = self.ensure_one().sudo()
        pdf_bytes = base64.b64decode(self.pdf_document_id.pre_signed_pdf)
        sign.user_ca_data_id = user_ca
        signed_pdf = sign.sign_pdf(pdf_bytes, **kwargs)
        sign.set_signed(user_execution=user_execution)
        sign.pdf_document_id.set_signed_pdf(signed_pdf)
        return True

    def action_open_sign_wizard(self):
        self.ensure_one()
        _logger.info("call action_open_sign_wizard call")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Select Certificate',
            'res_model': 'sign.ca.select.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_pdf_sign_id': self.id,
                'default_user_id': self.env.user.id,
                'user_ca_data_id': self.user_ca_data_id.id,
            }
        }

    def verify_approval(self, signatures):
        result = []
        for line in self.signature_ids:
            sig = next(
                (
                    s for s in signatures
                    if s["field_name"] == line.signature_field
                ),
                None,
            )
            data = {
                'pdf_sign': line
            }
            result.append(sig)
            if not sig:
                data['message'] = "%s belum ditandatangani." % line.name
                continue

            data['sig'] = sig

            if not sig["valid"]:
                data['message'] = "%s signature invalid." % line.name
                continue

            if sig["ca"].id != line.user_ca_data_id.id:
                data['message'] = "%s harus menggunakan CA %s." % (line.name, line.user_ca_data_id.name,)

        return result
