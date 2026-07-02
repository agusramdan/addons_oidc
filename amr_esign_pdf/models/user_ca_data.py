
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError


def decode_ca_data_bytes(data):
        data = (data or '').strip()
        if not data:
            return None
        if data.startswith('-----BEGIN'):
            return data.encode('utf-8')
        return base64.b64decode(data)


class UserCaData(models.Model):
    _name = 'user.ca.data'
    _description = 'User CA Data'
    _order = 'name'

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    certificate = fields.Text('Certificate')
    private_key = fields.Text('Private Key')
    public_key = fields.Text('Public Key')
    
    def load_signer_from_ca_data(self):
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization
            from asn1crypto import x509 as asn1_x509, keys as asn1_keys
            from pyhanko_certvalidator import registry
            from pyhanko.keys import (
                load_private_key_from_pemder_data,
                load_certs_from_pemder_data,
            )
            from pyhanko.sign.signers import SimpleSigner
            from pyhanko_certvalidator.registry import SimpleCertificateStore

        except ImportError:
            raise UserError(_('Cryptography, asn1crypto, and pyHanko are required to use CA data for signing.'))
        
        ca_data = self.ensure_one()
        certificate_bytes = decode_ca_data_bytes(ca_data.certificate)
        private_key_bytes = decode_ca_data_bytes(ca_data.private_key)
        certs = list(load_certs_from_pemder_data(certificate_bytes))
        private_key = load_private_key_from_pemder_data(private_key_bytes, passphrase=None)

        store = SimpleCertificateStore()

        for cert in certs:
            store.register(cert)

        return SimpleSigner(
            signing_cert=certs[0],
            signing_key=private_key,
            cert_registry=store,
        )
