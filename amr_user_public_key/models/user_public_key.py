# -*- coding: utf-8 -*-

import logging
import jwt

from jwt import InvalidTokenError
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import UnsupportedAlgorithm

from odoo import api, fields, models
from odoo.http import request

from odoo import models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class UserPublicKey(models.Model):
    _name = "user.public.key"
    _description = "Key untuk signature"

    active = fields.Boolean(default=True)
    user_id = fields.Many2one("res.users")
    device_id = fields.Char()
    kid = fields.Char()
    public_key = fields.Text()
    device_name = fields.Char()
    last_seen = fields.Datetime()
    revoked = fields.Boolean()

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
        default="ES256",
    )

    @api.constrains('public_key')
    def _check_public_key(self):
        for rec in self:
            try:
                serialization.load_pem_public_key(
                    rec.public_key.encode()
                )

            except (ValueError, UnsupportedAlgorithm):
                raise ValidationError("Invalid public key")

    def get_public_key(self, user, token):
        header = jwt.get_unverified_header(token)
        kid = header.get('kid')
        alg = header.get('alg')
        return self.search([('user_id', '=', user.id), ('kid', '=', kid), ('algorithm', '=', alg)]
                           , limit=1)

    def decode(self, token, **kw):
        if not self:
            return None
        self.ensure_one()
        return jwt.decode(token, key=self.public_key, algorithms=[self.algorithm])
