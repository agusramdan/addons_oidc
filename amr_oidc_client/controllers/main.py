# -*- coding: utf-8 -*-

import json

from odoo import http
from odoo.http import request


class MyApi(http.Controller):

    @http.route(
        '/api/test',
        type='http',
        auth='oidc',
        methods=['GET'],
        csrf=False
    )
    def test(self):
        user = request.env.user
        return request.make_response(json.dumps({
            'success': True,
            'uid': request.uid,
            'name': user.name
        }), headers=[("Content-Type", "application/json")])
