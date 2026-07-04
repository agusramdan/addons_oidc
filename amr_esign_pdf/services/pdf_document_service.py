# -*- coding: utf-8 -*-

import base64
import io

from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers

from cryptography.hazmat.primitives import serialization
from cryptography import x509

from asn1crypto import x509 as asn1_x509
from asn1crypto import keys

from odoo import models
from odoo.exceptions import UserError

class PdfDocumentService(models.AbstractModel):
    _name = 'pdf.document.service'
    _description = 'PDF Document Service'

    def prepare_pdf_lock(self, pdf_document, signature_specs):
        return pdf_document._prepare_pdf_lock(pdf_document.pdf_file, signature_specs)

    def generate_pdf_hash(self, pdf_document):
        return pdf_document.pdf_hash

    def sign_pdf_document(self,pdf_document,ca=None):

        ca = ca or self.env['user.ca.data'].search([
            ('user_id', '=', self.env.user.id)
        ], limit=1)

        if not ca:
            raise UserError("Certificate not found.")

        pdf_bytes = base64.b64decode(pdf_document.pdf_file)

        #
        # Load certificate
        #
        cert = x509.load_pem_x509_certificate(
            ca.certificate.encode()
        )

        cert = asn1_x509.Certificate.load(
            cert.public_bytes(serialization.Encoding.DER)
        )

        #
        # Load private key
        #
        private_key = serialization.load_pem_private_key(
            ca.private_key.encode(),
            password=None,
        )

        private_key = keys.PrivateKeyInfo.load(
            private_key.private_bytes(
                serialization.Encoding.DER,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )

        signer = signers.SimpleSigner(
            signing_cert=cert,
            signing_key=private_key,
            cert_registry=signers.SimpleCertificateStore(),
        )

        meta = signers.PdfSignatureMetadata(
            field_name="Signature1",
            md_algorithm="sha256",
        )

        writer = IncrementalPdfFileWriter(
            io.BytesIO(pdf_bytes)
        )

        output = io.BytesIO()

        pdf_signer = signers.PdfSigner(
            signature_meta=meta,
            signer=signer,
        )

        pdf_signer.sign_pdf(
            writer,
            output=output,
        )

        pdf_document.signed_pdf = base64.b64encode(
            output.getvalue()
        )
