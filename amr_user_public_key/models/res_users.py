# -*- coding: utf-8 -*-

import logging
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import werkzeug

from odoo import api, models, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    def decode(self, token, **kw):
        # Chek apakah user mempunyak token priadi yang bisa di chek
        public_key = self.env['user.public.key'].get_public_key(self, token)
        return public_key.decode(token,**kw) or super().decode(token,**kw)
