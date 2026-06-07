# -*- coding: utf-8 -*-

import logging
import jwt
import requests
import re

from jwt import PyJWKClient, InvalidTokenError
from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)

AUTHORIZATION_RE = re.compile(r"^Bearer ([^ ]+)$")


class ResourceAccessToken(models.AbstractModel):
    _inherit = 'amr.resource.helper'

    @api.model
    def get_audiences(self, issuer=None):
        if not issuer:
            issuer = self.get_issuer()
        audiences_text = self.env['ir.config_parameter'].sudo().get_param('amr_auto_login.audience', '')
        audiences = audiences_text.split()
        audiences.append(super().get_audiences(issuer=issuer))
        # hack now audience is issuer
        if issuer not in audiences:
            audiences.append(issuer)
        return audiences
