# -*- coding: utf-8 -*-

import logging
import werkzeug

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from odoo import models
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    def add_url_access_token(self, url=None, create=True, param_name='access_token'):
        access_token = self.get_access_token(create=create)
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        query_params[param_name] = access_token
        new_query = urlencode(query_params, doseq=True)
        return urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment,
        ))

    def get_auto_login_url(self, url=None, create=True, web_token_access_path='/web_token_access'):
        token = self.get_access_token(create=create)
        query = {'token_access': token}
        url = url or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        result = urlparse(url)
        redirect = result.path or ""
        if result.fragment:
            if redirect:
                redirect = f"{redirect}#{result.fragment}"
            else:
                redirect = f"/#{result.fragment}"
        if redirect:
            query['redirect'] = redirect
        query_str = werkzeug.url_encode(query)
        return "%s://%s%s?%s" % (result.scheme, result.netloc, web_token_access_path, query_str)

    def get_mobile_access_token(self, create=False):
        return self.get_access_token(create=create)

    def get_access_token(self, create=False, scope='', audience=''):
        return self.env['amr.token'].get_access_token(user=self, create=create, scope=scope, audience=audience)

    def create_access_token(self, scope='', audience=''):
        return self.env['amr.token'].create_access_token(user=self,  scope=scope, audience=audience)
