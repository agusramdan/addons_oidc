from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class UserCaDataWizard(models.TransientModel):
    _name = 'user.ca.data.wizard'
    _description = 'User CA Data Wizard'

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    key_algorithm = fields.Selection(
        [
            # https://pyjwt.readthedocs.io/en/stable/algorithms.html
            ("ES256", "ES256 - ECDSA using SHA-256"),
            ("ES256K", "ES256K - ECDSA with secp256k1 curve using SHA-256"),
            ("ES384", "ES384 - ECDSA using SHA-384"),
            ("ES512", "ES512 - ECDSA using SHA-512"),
            ("RS256", "RS256 - RSASSA-PKCS1-v1_5 using SHA-256"),
            ("RS384", "RS384 - RSASSA-PKCS1-v1_5 using SHA-384"),
            ("RS512", "RS512 - RSASSA-PKCS1-v1_5 using SHA-512"),
            ("PS256", "PS256 - RSASSA-PSS using SHA-256 and MGF1 padding with SHA-256"),
            ("PS384", "PS384 - RSASSA-PSS using SHA-384 and MGF1 padding with SHA-384"),
            ("PS512", "PS512 - RSASSA-PSS using SHA-512 and MGF1 padding with SHA-512"),
        ],
        default="RS256",
        string='Key Algorithm',
    )
    validity_days = fields.Integer('Validity (days)', default=365)
    certificate = fields.Text('Certificate')
    private_key = fields.Text('Private Key')
    private_key_password = fields.Char('Private Key Password')

    def action_generate_keypair(self):
        self.ensure_one()
        self._generate_self_signed_ca()
        return {
            "type": "ir.actions.act_window",
            "name": self._description,
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context
        }

    def action_create_ca_data(self):
        self.ensure_one()
        if not self.certificate or not self.private_key:
            self._generate_self_signed_ca()
        if not self.certificate or not self.private_key:
            raise UserError(_('Certificate and private key must be provided.'))
        self.env['user.ca.data'].create({
            'name': self.name,
            'user_id': self.user_id.id,
            'certificate': self.certificate,
            'private_key': self.private_key,
        })
        return {'type': 'ir.actions.act_window_close'}

    def _generate_self_signed_ca(self):
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import ec, rsa
            from cryptography.x509.oid import NameOID
        except ImportError:
            raise UserError(_('Cryptography is required to generate CA key and certificate.'))

        if not self.name:
            raise UserError(_('CA name is required to generate a certificate.'))

        password = self.private_key_password.encode('utf-8') if self.private_key_password else None
        if self.key_algorithm in ('ES256', 'ES256K'):
            curve = ec.SECP256R1() if self.key_algorithm == 'ES256' else ec.SECP256K1()
            private_key = ec.generate_private_key(curve, backend=default_backend())
        elif self.key_algorithm == 'ES384':
            private_key = ec.generate_private_key(ec.SECP384R1(), backend=default_backend())
        elif self.key_algorithm == 'ES512':
            private_key = ec.generate_private_key(ec.SECP521R1(), backend=default_backend())
        elif self.key_algorithm in ('RS256', 'RS384', 'RS512', 'PS256', 'PS384', 'PS512'):
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        else:
            raise UserError(_('Unsupported key algorithm: %s') % self.key_algorithm)

        signature_hash = {
            'ES256': hashes.SHA256(),
            'ES256K': hashes.SHA256(),
            'ES384': hashes.SHA384(),
            'ES512': hashes.SHA512(),
            'RS256': hashes.SHA256(),
            'RS384': hashes.SHA384(),
            'RS512': hashes.SHA512(),
            'PS256': hashes.SHA256(),
            'PS384': hashes.SHA384(),
            'PS512': hashes.SHA512(),
        }[self.key_algorithm]

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, self.name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, _('Odoo ESign PDF')),  # noqa: F821
        ])
        now = datetime.utcnow()
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=self.validity_days or 365))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(private_key, signature_hash, default_backend())
        )

        private_format = serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=private_format,
        )
        certificate_bytes = certificate.public_bytes(serialization.Encoding.PEM)

        self.private_key = private_bytes.decode('utf-8')
        self.certificate = certificate_bytes.decode('utf-8')
