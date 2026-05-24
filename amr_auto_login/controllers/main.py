# -*- coding: utf-8 -*-

import base64
import logging
import json
import werkzeug

from werkzeug import url_encode

from odoo import fields, http

_logger = logging.getLogger(__name__)


class ControllerAccess(http.Controller):

    @http.route(['/web_token_access'], type='http', auth='auto_login', methods=['GET'], csrf=False)
    def web_token_access(self, redirect=None, **kw):
        if redirect:
            url = redirect
        elif kw:
            url = "/web#%s" % url_encode(kw)
        else:
            url = "/web"
        return werkzeug.utils.redirect(url)
