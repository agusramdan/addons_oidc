import base64
from odoo.tests.common import TransactionCase


class TestPdfEsign(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})

    def test_prepare_and_sign_flow(self):
        # create a minimal PDF bytes
        pdf_bytes = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\ntrailer\n<< /Root 1 0 R >>\n%%EOF'
        pdf_b64 = base64.b64encode(pdf_bytes).decode('ascii')

        doc = self.env['pdf.document'].create({
            'name': 'Doc 1',
            'pdf_file': pdf_b64,
            'pdf_filename': 'doc.pdf',
        })

        # hash must be computed
        self.assertTrue(doc.pdf_hash)

        # prepare signature (creates pdf_lock)
        doc.action_prepare_signature()
        self.assertEqual(doc.state, 'request')
        self.assertTrue(doc.pdf_lock)

        # create signature record and send request
        sign = self.env['pdf.sign'].create({
            'name': 'Sig1',
            'pdf_document_id': doc.id,
            'partner_id': self.partner.id,
            'signature_index': 1,
        })
        sign.action_send()
        self.assertEqual(sign.state, 'send')

        # simulate CA returning CMS and applying it
        cms = base64.b64encode(b'fakecms').decode('ascii')
        sign.cms_data = cms
        sign.action_apply_cms()
        self.assertEqual(sign.state, 'signed')

        # finalize document signing
        doc.action_sign_pdf()
        self.assertEqual(doc.state, 'signed')
        self.assertTrue(doc.signed_pdf)
