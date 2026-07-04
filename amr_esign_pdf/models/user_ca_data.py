# -*- coding: utf-8 -*-

import logging
import base64

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
# from cryptography.hazmat.primitives import serialization
# from asn1crypto import x509 as asn1_x509, keys as asn1_keys
# from pyhanko_certvalidator import registry
from pyhanko.keys import (
    load_private_key_from_pemder_data,
    load_certs_from_pemder_data,
)
from pyhanko.sign.signers import Signer, SimpleSigner
# from pyhanko.sign.signers.csc_signer import CSCSigner, PrefetchedSADAuthorizationManager,CSCAuthorizationInfo,CSCServiceSessionInfo,CSCCredentialInfo
from pyhanko_certvalidator.registry import SimpleCertificateStore

from odoo import api, fields, models, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

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
    _order = 'not_valid_after desc, name'

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    auto_signature = fields.Boolean(
        help="Signature by system not need authentication."
    )
    signature_scope = fields.Selection([
        ("internal", "Internal"),
        ("partner", "Partner"),
        ("public", "Public"),
    ], default="internal")
    provider = fields.Selection(
        [('internal', 'Internal CA'), ("pkcs12", "PKCS#12"), ("pkcs11", "PKCS#11"),
         ("csc", "Cloud Signature Consortium"), ],
        default='internal',
        string='Provider',
    )
    algorithm = fields.Selection(
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
    not_valid_before = fields.Datetime("Started")
    not_valid_after = fields.Datetime("Expired")
    serial_number = fields.Char()
    certificate = fields.Text('Certificate', help="PEM Format")
    private_key = fields.Text('Private Key', help="Hanya untuk develpment mode internal")
    public_key = fields.Text('Public Key')
    password = fields.Char("Password")
    certificate_fingerprint = fields.Char(index=True)
    certificate_subject = fields.Char()
    certificate_issuer = fields.Char()

    # configuration Cloud Signature Consortium
    csc_service_url = fields.Char()  # "https://sign.example.com",
    csc_credential_id = fields.Char(
        help="""
Credential ini biasanya mewakili:

satu user
satu sertifikat
satu private key

Sehingga pada praktiknya credentialID sering menjadi identitas signer.        
        """
    )
    # "credential123",
    csc_oauth_token = fields.Char()
    csc_token_expires_at = fields.Datetime()

    def create_user_ca(self, **kwargs):
        return self.create(kwargs)

    def create_self_signed_ca(self, user, algorithm='RS256', common_name=None, org_name=None, validity_days=None,
                              **kwargs):
        dict_data = self.generate_self_signed_ca(
            user, algorithm, common_name=common_name or user.name, org_name=org_name, validity_days=validity_days
        )
        data = dict(kwargs)
        data.update(dict_data)
        data.setdefault('name', user.name)
        data.setdefault('user_id', user.id)
        return self.create_user_ca(**data)

    def _compute_certificate_info(self):
        for rec in self:
            if not rec.certificate:
                continue

            cert = x509.load_pem_x509_certificate(
                rec.certificate.encode(),
                default_backend()
            )

            rec.serial_number = format(cert.serial_number, "X")
            rec.certificate_subject = cert.subject.rfc4514_string()
            rec.certificate_issuer = cert.issuer.rfc4514_string()
            rec.certificate_fingerprint = cert.fingerprint(
                hashes.SHA256()
            ).hex().upper()

    def find_auto_signature_user(self, user):
        return self or self.search([('user_id', '=', user.id)], limit=1)

    @api.model
    def find_by_certificate(self, cert):

        fingerprint = cert.fingerprint(
            hashes.SHA256()
        ).hex().upper()

        return self.search([
            ("certificate_fingerprint", "=", fingerprint)
        ], limit=1)

    def verify_signatures(self, signatures):

        result = []

        UserCA = self.env["user.ca.data"]

        for sig in signatures:
            ca = UserCA.find_by_certificate(sig["certificate"])

            result.append({
                "field_name": sig["field_name"],
                "valid": sig["valid"],
                "ca": ca,
                "user": ca.user_id if ca else False,
            })

        return result

    def load_signer_from_ca_data(self, password=None, dry_run=False):
        ca_data = self.ensure_one()
        if not self.user_has_groups(
                'amr_esign_pdf.group_pdf_sign_admin') and not dry_run and not ca_data.auto_signature and ca_data.user_id.id != self.env.uid:
            raise UserError("You cannot signer other user.")

        if ca_data.provider == 'internal':
            passphrase = None
            password = password or ca_data.password
            if password and isinstance(password, str):
                passphrase = password.encode("utf-8")
            certificate_bytes = decode_ca_data_bytes(ca_data.certificate)
            private_key_bytes = decode_ca_data_bytes(ca_data.private_key)
            certs = list(load_certs_from_pemder_data(certificate_bytes))
            private_key = load_private_key_from_pemder_data(private_key_bytes, passphrase=passphrase)
            if dry_run:
                return Signer()

            store = SimpleCertificateStore()

            for cert in certs:
                store.register(cert)

            return SimpleSigner(
                signing_cert=certs[0],
                signing_key=private_key,
                cert_registry=store,
            )
        elif ca_data.provider == 'csc':
            # csc_session_info = CSCServiceSessionInfo()
            # credential_info = CSCCredentialInfo()
            # # auth_manager=CSCAuthorizationManager(csc_session_info=csc_session_info,credential_info=credential_info)
            # csc_auth_info = CSCAuthorizationInfo()
            # auth_manager = PrefetchedSADAuthorizationManager(
            #     csc_session_info=csc_auth_info,
            #     credential_info=credential_info,
            #     # csc_auth_info=csc_auth_info,
            # )
            # csc_session_info=csc_session_info,
            # credential_info=credential_info,
            # csc_auth_info=csc_auth_info, )
            # return CSCSigner(
            #     session=aiohttp.ClientSession(),
            #     auth_manager=auth_manager,
            # )
            pass

        raise ValueError(_("Provider %s not support.") % ca_data.provider)

    @api.model
    def generate_self_signed_ca(self, user, algorithm, common_name=None, org_name=None, validity_days=None):
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import ec, rsa
            from cryptography.x509.oid import NameOID
        except ImportError:
            raise UserError(_('Cryptography is required to generate CA key and certificate.'))

        if not user:
            raise UserError(_('User is required to generate a certificate.'))

        # algorithm = self.algorithm
        if algorithm in ('ES256', 'ES256K'):
            curve = ec.SECP256R1() if algorithm == 'ES256' else ec.SECP256K1()
            private_key = ec.generate_private_key(curve, backend=default_backend())
        elif algorithm == 'ES384':
            private_key = ec.generate_private_key(ec.SECP384R1(), backend=default_backend())
        elif algorithm == 'ES512':
            private_key = ec.generate_private_key(ec.SECP521R1(), backend=default_backend())
        elif algorithm in ('RS256', 'RS384', 'RS512', 'PS256', 'PS384', 'PS512'):
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        else:
            raise UserError(_('Unsupported key algorithm: %s') % algorithm)

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
        }[algorithm]

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name or user.name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, org_name or _('Odoo ESign PDF')),
        ])
        now = datetime.utcnow()
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=validity_days or 365))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(private_key, signature_hash, default_backend())
        )

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        certificate_bytes = certificate.public_bytes(serialization.Encoding.PEM)

        return dict(
            serial_number=str(certificate.serial_number),
            private_key=private_bytes.decode('utf-8'),
            public_key=public_bytes.decode('utf-8'),
            certificate=certificate_bytes.decode('utf-8'),
        )
