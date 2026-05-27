import uuid
import hashlib
from psycopg2 import IntegrityError
from odoo import api, fields, models
from odoo.exceptions import UserError


class AuthChallenge(models.Model):
    _name = "auth.challenge"
    active = fields.Boolean(default=True)
    challenge_token = fields.Char()
    nonce = fields.Char()

    action = fields.Selection([
        ("login", "Login"),
        ("approve", "Approve"),
        ("reject", "Reject"),
    ])

    status = fields.Selection([
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("expired", "Expired")
    ])
    session_sid = fields.Char()
    requested_by = fields.Many2one("res.users")
    approved_by = fields.Many2one("res.users")
    # device_id = fields.Many2one("auth.device")
    expired_at = fields.Datetime()
