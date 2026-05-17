# -*- coding: utf-8 -*-

import base64
import logging
import jwt
import time

from datetime import datetime, timedelta

from jwt import InvalidTokenError
from odoo import api, fields, models
from datetime import timedelta
from urllib.parse import urlencode

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


import uuid

from odoo import models, fields


class OidcAuthorizationCode(models.Model):
    _name = 'oidc.authorization.code'
    _description = 'OIDC Authorization Code'

    code = fields.Char(
        default=lambda self: str(uuid.uuid4()),
        required=True,
        index=True
    )
    client_id = fields.Many2one(
        'oidc.client',
        required=True
    )
    user_id = fields.Many2one(
        'res.users',
        required=True
    )
    redirect_uri = fields.Text(required=True)
    scope = fields.Char()
    expired_at = fields.Datetime(required=True)
    used = fields.Boolean(default=False)

    def cron_cleanup_tokens(self):
        tokens = self.search([('expired_at', '<', fields.Datetime.now())])
        tokens.unlink()
