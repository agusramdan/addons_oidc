# -*- coding: utf-8 -*-

from werkzeug.exceptions import Unauthorized
from odoo import fields, models
from odoo.http import request
from odoo.service import security


class OidcClientKey(models.Model):
    _name = 'oidc.client.key'

    client_id = fields.Many2one('oidc.client')
    kid = fields.Char()
    algorithm = fields.Char(default="RS256", )
    kty = fields.Selection([
        ("RSA", "RSA"),
        ("EC", "EC"),
        ("OKP", "OKP"),
    ])
    use = fields.Selection([
        ("sig", "Signature"),
        ("enc", "Encryption"),
    ], default="sig")

    public_key = fields.Text()
    active = fields.Boolean(default=True)
    expired_at = fields.Datetime()
    last_used_at = fields.Datetime()
