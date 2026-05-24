# -*- coding: utf-8 -*-

import logging
import jwt

from jwt import InvalidTokenError
from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)

from odoo import models, fields


class UserPublicKey(models.Model):
    _name = "amr.user.public.key"
    _description = "Key untuk signature"

    user_id = fields.Many2one("res.users")
    device_id = fields.Char(required=True)
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
