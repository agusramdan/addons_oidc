# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import base64
import logging
import json
import io
import qrcode

import uuid
import jwt
import datetime

from werkzeug.wrappers import Response

from odoo import api, http, fields
from odoo.http import request
from werkzeug.exceptions import BadRequest, Conflict, NotFound
from werkzeug.utils import redirect
from odoo.addons.amr_resource.exceptions import handle_exception

_logger = logging.getLogger(__name__)


class PdfDocumentAPI(http.Controller):

    @api.model
    def generate_qr(self, deep_link, version=2, box_size=10, border=1):
        qr = qrcode.QRCode(version=version, box_size=box_size, border=border)
        qr.add_data(deep_link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return request.make_response(
            buffer.getvalue(),
            headers=[
                ('Content-Type', 'image/png')
            ]
        )

    @http.route('/qr/<deep_link_hash>/<model>/<int:rec_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_token(self, deep_link_hash, model, rec_id, **kwargs):
        # response token
        if model not in request.env:
            raise NotFound

        challenge = request.env[model].sudo().browse(rec_id)
        if not challenge.exists() and challenge.deep_link_hash != deep_link_hash:
            return request.not_found()

        # bila redirect internal_url
        if kwargs.get('view_type', 'qr') == 'qr':
            return self.generate_qr(challenge.deep_link)

        if model == 'pdf.sign':
            return redirect("/pdf/sign/%s/%s" % (challenge.deep_link_hash, challenge.id))
        return redirect(challenge.internal_url)



    @http.route('/api/v1/document/submit', type='http', auth='machine', methods=['POST'], csrf=False)
    def submit(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.data.decode('utf-8') or '{}')
        except ValueError:
            return request.make_response(json.dumps({'status': 'error', 'data': 'Invalid JSON payload.'}),
                                         [('Content-Type', 'application/json')])

        name = payload.get('name')
        # provider = payload.get('provider')
        pdf_file = payload.get('pdf_file')
        # if not name or not provider or not pdf_file:
        #     return request.make_response(json.dumps({'status': 'error', 'data': 'Missing required fields: name, provider, pdf_file.'}), [('Content-Type', 'application/json')])

        document = request.env['pdf.document'].sudo().create({
            'name': name,
            'pdf_file': pdf_file,
            'pdf_filename': payload.get('pdf_filename') or '%s.pdf' % name,
        })

        return request.make_response(
            json.dumps(
                {'status': 'success', 'data': {'id': document.id, 'name': document.name, 'state': document.state}}),
            [('Content-Type', 'application/json')],
        )
