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

        sign = self.env['pdf.sign'].create({
            'name': 'Sig1',
            'pdf_document_id': doc.id,
            'partner_id': self.partner.id,
            'signature_index': 1,
            'signature_name': 'Signature1'
        })

        # hash must be computed from the original document
        self.assertTrue(doc.pdf_hash)

        # prepare signature (creates pdf_lock with placeholder)
        doc.action_prepare_signature()
        self.assertEqual(doc.state, 'request')
        self.assertTrue(doc.pdf_lock)
        self.assertNotEqual(doc.pdf_lock, doc.pdf_file)

        sign.action_send()
        self.assertEqual(sign.state, 'requested')

        # create active internal CA and perform sign-by-user flow
        ca_wizard = self.env['user.ca.data.wizard'].create({
            'name': 'Test CA',
            'user_id': self.env.user.id,
        })
        ca_wizard._generate_self_signed_ca()
        self.env['user.ca.data'].create({
            'name': 'Test CA Active',
            'user_id': self.env.user.id,
            'certificate': ca_wizard.certificate,
            'private_key': ca_wizard.private_key,
            'private_key_password': ca_wizard.private_key_password,
            'state': 'active',
        })

        sign.action_sign_by_user()
        self.assertEqual(sign.state, 'signed')
        self.assertEqual(doc.state, 'signed')
        self.assertTrue(doc.signed_pdf)
