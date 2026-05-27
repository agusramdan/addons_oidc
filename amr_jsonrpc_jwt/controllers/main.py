# -*- coding: utf-8 -*-

import json

from odoo import http
from odoo.http import request

from odoo.api import call_kw, Environment
from odoo import http, tools
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception, Response
from odoo.models import check_method_name


class JsonRpcApi(http.Controller):

    def _call_kw(self, model, method, args, kwargs):
        check_method_name(method)
        return call_kw(request.env[model], method, args, kwargs)

    @http.route('/api/dataset/call', type='json', auth="jwt")
    def call(self, model, method, args, domain_id=None, context_id=None):
        return self._call_kw(model, method, args, {})

    @http.route(['/api/dataset/call_kw', '/api/dataset/call_kw/<path:path>'], type='json', auth="jwt")
    def call_kw(self, model, method, args, kwargs, path=None):
        return self._call_kw(model, method, args, kwargs)
