# -*- coding: utf-8 -*-

import base64
import json
import binascii
import io
import uuid

from pyhanko.pdf_utils.content import PdfContent
from pyhanko.pdf_utils.layout import BoxConstraints
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.stamp import QRStampStyle, StaticStampStyle, QRPosition

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import base64
import binascii
import io
import uuid

from pyhanko.pdf_utils.content import PdfContent
from pyhanko.pdf_utils.layout import (
    BoxConstraints,
    SimpleBoxLayoutRule,
    InnerScaling,
    AxisAlignment,
)
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.stamp import StaticStampStyle

qr_position_map = {
    'LEFT_OF_TEXT': QRPosition.LEFT_OF_TEXT,
    'RIGHT_OF_TEXT': QRPosition.RIGHT_OF_TEXT,
    'ABOVE_TEXT': QRPosition.ABOVE_TEXT,
    'BELOW_TEXT': QRPosition.BELOW_TEXT,
}


def render_stamp(pdf_bytes, values):
    """
    Render AcroForm PDF fields dengan nilai yang diberikan.
    """
    import fitz
    import io

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Index field berdasarkan nama agar pencarian lebih cepat
    widgets = {}

    for page in doc:
        for widget in page.widgets():
            widgets[widget.field_name] = widget

    # Isi seluruh field
    for field_name, value in values.items():

        widget = widgets.get(field_name)

        if not widget:
            continue

        if value is None:
            value = ""

        # Text Field
        if widget.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
            widget.field_value = str(value)
            widget.update()

        # Check Box
        elif widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
            widget.field_value = bool(value)
            widget.update()

        # Combo Box
        elif widget.field_type == fitz.PDF_WIDGET_TYPE_COMBOBOX:
            widget.field_value = str(value)
            widget.update()

        # List Box
        elif widget.field_type == fitz.PDF_WIDGET_TYPE_LISTBOX:
            widget.field_value = str(value)
            widget.update()

        # Radio Button
        elif widget.field_type == fitz.PDF_WIDGET_TYPE_RADIOBUTTON:
            widget.field_value = str(value)
            widget.update()

    output = io.BytesIO()

    doc.save(
        output,
        garbage=4,
        deflate=True,
    )

    doc.close()

    return output.getvalue()


class ImportedPdfBytes(PdfContent):

    def __init__(
            self,
            pdf_bytes,
            width,
            height,
            page_ix=0,
    ):
        super().__init__()

        self.pdf_bytes = pdf_bytes
        self.page_ix = page_ix
        self.target_width = width
        self.target_height = height

    def render(self):
        writer = self._ensure_writer

        reader = PdfFileReader(
            io.BytesIO(self.pdf_bytes)
        )

        xobj = writer.import_page_as_xobject(
            reader,
            page_ix=self.page_ix,
        )

        resource_name = (
                b'/Import' +
                binascii.hexlify(uuid.uuid4().bytes)
        )

        self.resources.xobject[
            resource_name.decode('ascii')
        ] = xobj

        # Source PDF dimensions
        x1, y1, x2, y2 = xobj.get_object()['/BBox']

        source_width = abs(float(x2) - float(x1))
        source_height = abs(float(y2) - float(y1))

        # Scale source -> target
        scale_x = self.target_width / source_width
        scale_y = self.target_height / source_height

        # Content box = target size
        self.box = BoxConstraints(
            width=self.target_width,
            height=self.target_height,
        )

        return (
                b'q\n'
                + (
                    f'{scale_x} 0 0 {scale_y} 0 0 cm\n'
                ).encode('ascii')
                + resource_name
                + b' Do\n'
                + b'Q\n'
        )


class PdfSignTemplate(models.Model):
    _name = "pdf.sign.template"
    _description = "PDF Signature Template"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    offset_x = fields.Float(default=0)
    offset_y = fields.Float(default=0)
    width = fields.Float("Width (pt)", default=180, )
    height = fields.Float("Height (pt)", default=70, )
    width_mm = fields.Float("Width (mm)", compute="_compute_size_mm", store=True, )
    height_mm = fields.Float("Height (mm)", compute="_compute_size_mm", store=True, )
    border_width = fields.Float("Border Width (pt)", default=0, )
    template_type = fields.Selection([
        ("signature", "Signature"),
        ("stamp", "Stamp"),
        ("watermark", "Watermark"),
    ], default="signature")

    renderer = fields.Selection([
        ("pdf", "PDF AcroForm"),
        ("qweb", "QWeb Template"),
        ("text", "Text Template"),
    ], default="pdf", required=True)

    pdf_template = fields.Binary()
    pdf_template_filename = fields.Char()

    qweb_view_id = fields.Many2one(
        "ir.ui.view",
        domain=[("type", "=", "qweb")],
        string="QWeb Template"
    )
    report_id = fields.Many2one(
        "ir.actions.report",
        string="Report",
        readonly=True
    )
    paper_format_id = fields.Many2one(
        "report.paperformat",
        string="Paper Format",
        readonly=True
    )
    qr_position = fields.Selection([
        ("LEFT_OF_TEXT", "LEFT_OF_TEXT"),
        ("RIGHT_OF_TEXT", "RIGHT_OF_TEXT"),
        ("ABOVE_TEXT", "ABOVE_TEXT"),
        ("BELOW_TEXT", "BELOW_TEXT"),
    ], default="LEFT_OF_TEXT", )

    text_template = fields.Text(
        default="Ditandatangani secara digital\n\n"
                "%(signer_name)s \n"
                "Timestamp: %(ts)s \n"
                "Scan QR untuk verifikasi\n"
    )
    render_config = fields.Text(
        default='{"version":1,"fields":[]}',
        help="JSON Render Configuration"
    )

    preview = fields.Binary(
        readonly=True,
    )

    notes = fields.Text()

    @api.depends("width", "height")
    def _compute_size_mm(self):
        factor = 25.4 / 72.0
        for record in self:
            record.width_mm = record.width * factor
            record.height_mm = record.height * factor

    @api.model
    def pdf_pt_to_mm(self, value):
        return value * 25.4 / 72.0

    @api.model
    def pdf_mm_to_pt(self, value):
        return value * 72.0 / 25.4

    def _create_paper_format(self):
        self.ensure_one()
        vals = {
            "name": "PDF Sign - Paper Format - %s" % self.name,
            "format": "custom",
            "page_width": self.pdf_pt_to_mm(self.width),
            "page_height": self.pdf_pt_to_mm(self.height),
            "orientation": "Portrait",
            "margin_top": 0,
            "margin_bottom": 0,
            "margin_left": 0,
            "margin_right": 0,
            "header_line": False,
            "dpi": 96,
        }
        paper_format_id = self.paper_format_id
        if paper_format_id:
            paper_format_id.write(vals)
        else:
            paper_format_id = self.env["report.paperformat"].create(vals)
            self.write({
                'paper_format_id': paper_format_id.id
            })
        return paper_format_id

    def _create_report(self):
        self.ensure_one()

        paper_format = self._create_paper_format()

        vals = {
            "name": "PDF Sign - Report - %s" % self.name,
            "model": "pdf.sign.data",
            "report_type": "qweb-pdf",
            "report_name": self.qweb_view_id.key,
            "report_file": self.qweb_view_id.key,
            "paperformat_id": paper_format.id,
        }
        report_id = self.report_id
        if self.report_id:
            report_id.write(vals)
        else:
            report_id = self.env["ir.actions.report"].create(vals)
            self.write({
                'report_id':report_id.id
            })

        return report_id

    def write(self, vals):
        res = super(PdfSignTemplate, self).write(vals)

        if {"width", "height", "qweb_view_id"}.intersection(vals):
            for record in self:
                if record.qweb_view_id:
                    record.sudo()._create_report()

        return res

    def unlink(self):
        reports = self.mapped("report_id")
        paper_formats = self.mapped("paper_format_id")

        res = super(PdfSignTemplate, self).unlink()

        reports.unlink()
        paper_formats.unlink()

        return res

    def render(self, context):
        """
Render the template with the provided context.
:param context: A dictionary containing the context for rendering.
:return: The rendered PDF as a binary string.
render_config example:
{
  "version": 1,
  "page": 1,
  "background": true,
  "flatten": false,
  "fields": [
    {
      "name": "SIGNER",
      "source": "signer.name",
      "type": "text",
      "target": "txtSigner"
    },
    {
      "name": "DATE",
      "source": "sign_date",
      "type": "date",
      "format": "%d/%m/%Y %H:%M",
      "target": "txtDate"
    },
    {
      "name": "REASON",
      "source": "approval.reason",
      "type": "text",
      "target": "txtReason"
    },
    {
      "name": "QR",
      "source": "url",
      "type": "qr",
      "target": "imgQR"
    },
    {
      "name": "LOGO",
      "source": "company.logo",
      "type": "image",
      "target": "imgLogo"
    }
  ]
}

Sample context:
context = {
    "signer": signer,
    "approval": approval,
    "company": company,
    "certificate": cert,
    "url": "...",
}
        """
        # Here you would implement the logic to render the PDF template
        # using the provided context. This is a placeholder implementation.
        if not self.pdf_template:
            raise UserError(_("No PDF template available for rendering."))

        # For demonstration, we simply return the original PDF template.
        # In a real implementation, you would use a library like Jinja2
        # to replace placeholders in the PDF with values from the context.
        return base64.b64decode(self.pdf_template)

    def render_pdf(self, context):
        """
        Render the template with the provided context.

        :param context: dict
        :return: rendered pdf bytes
        """
        import base64
        import json
        from datetime import datetime, date

        self.ensure_one()

        if self.renderer == "pdf":
            if not self.pdf_template:
                raise UserError(_("No PDF template available for rendering."))
            try:
                config = json.loads(self.render_config or "{}")
            except Exception as ex:
                raise UserError(_("Invalid render configuration:\n%s") % ex)

            pdf_bytes = base64.b64decode(self.pdf_template)

            values = {}

            for field in config.get("fields", []):

                source = field.get("source")
                target = field.get("target")
                field_type = field.get("type", "text")
                default = field.get("default")

                # Resolve source
                value = context

                if source:
                    for attr in source.split("."):
                        if value is None:
                            break

                        if isinstance(value, dict):
                            value = value.get(attr)
                        else:
                            value = getattr(value, attr, None)

                if value is None:
                    value = default

                # Format value
                if value is not None:

                    if field_type == "date":
                        fmt = field.get("format", "%Y-%m-%d")
                        if isinstance(value, (datetime, date)):
                            value = value.strftime(fmt)

                    elif field_type == "datetime":
                        fmt = field.get("format", "%Y-%m-%d %H:%M:%S")
                        if isinstance(value, (datetime, date)):
                            value = value.strftime(fmt)

                    elif field_type == "text":
                        value = str(value)

                    elif field_type == "number":
                        value = str(value)

                    elif field_type == "boolean":
                        value = "Yes" if value else "No"

                    elif field_type in ("image", "qr", "barcode"):
                        # diproses oleh renderer
                        pass

                values[target] = value

            return render_stamp(pdf_bytes, values)

        elif self.renderer == "qweb":
            return self.generate_pdf_binary(render_data=context)

        raise UserError(_("Unknown renderer '%s'.") % self.renderer)

    def create_stamp_style(self, appearance_text_params):
        stamp_text = "Ditanda tangani secara digital\n\n" \
                     "%(signer_name)s \n" \
                     "Timestamp: %(ts)s \n" \
                     "Scan QR untuk verifikasi\n"
        if self:
            if self.renderer != "text":
                pdf_bytes = self.render_pdf(appearance_text_params)
                return self.create_pdf_stamp_style(pdf_bytes)
            elif self.text_template:
                stamp_text = self.text_template
        qr_position = qr_position_map[self.qr_position or 'LEFT_OF_TEXT']
        return QRStampStyle(
            border_width=self.border_width,
            stamp_text=stamp_text,
            qr_position=qr_position,
        )

    def create_pdf_stamp_style(self, pdf_bytes):
        return StaticStampStyle(
            border_width=self.border_width,
            background=ImportedPdfBytes(pdf_bytes, width=self.width, height=self.height, )
        )

    def create_signature_stamp(self, signature_pdf_b64):

        signature_pdf = base64.b64decode(
            signature_pdf_b64
        )

        content = ImportedPdfBytes(
            signature_pdf,
            width=self.width,
            height=self.height,
            page_ix=0,
        )

        return StaticStampStyle(
            background=content,
            border_width=0,
            background_layout=SimpleBoxLayoutRule(
                x_align=AxisAlignment.ALIGN_MID,
                y_align=AxisAlignment.ALIGN_MID,
                inner_content_scaling=InnerScaling.SHRINK_TO_FIT,
            ),
        )

    def generate_pdf_binary(self, render_data=None):
        self.ensure_one()

        if not self.qweb_view_id:
            raise UserError("QWeb Template belum ditentukan.")

        if not self.report_id:
            self.sudo()._create_report()

        render_data = render_data or {}
        qr = render_data.pop("qr",None) or {}
        url = qr.get('value') or render_data.get('url')
        if not qr.get('image') and url:
            qr['image']=self.env['deep.link.mixin'].generate_qr_base64(url)
        render_data.setdefault('qr',qr)
        doc = self.env["pdf.sign.data"].create({
            "template_id": self.id,
            "data_json": json.dumps(
                render_data,
                ensure_ascii=False,
            ),
        })
        pdf_binary, content_type = self.report_id.render_qweb_pdf(doc.ids)

        return pdf_binary

    def action_open_sign_preview_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Qweb Sign Preview',
            'res_model': 'pdf.sign.preview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.id,
                'default_user_id': self.env.user.id,
            }
        }
