# -*- coding: utf-8 -*-

from werkzeug.utils import redirect
from odoo.http import Controller, request, route
from odoo.api import call_kw
from odoo.models import check_method_name


class RedirectController(Controller):

    @route(['/redirect'], type='http', auth='user_or_param', methods=['GET'], csrf=False)
    def redirect_url(self, url=None):
        url = request.env.user.add_url_access_token(url)
        return redirect(url)

    @route(['/api/v1/access/url'], type='http', auth='user_or_param', methods=['GET'], csrf=False)
    def access_url(self, **kwargs):
        data = dict(kwargs)
        res_id = data.get("res_id", None)
        res_model = data.get("res_model", None)

        model_object = request.env[res_model].browse(res_id)
        if callable(getattr(model_object, 'get_url_access_token', None)):
            result = model_object.get_url_access_token()
        else:
            type_url = data.get("type_url", "internal")
            if type_url == 'internal':
                url = model_object.get_internal_url()
            else:
                url = model_object.get_public_url()

            access_url = request.env.user.add_url_access_token(url)
            result = {
                'url': url,
                'access_url': access_url,
            }
        return redirect(url)


class JsonRpcApi(Controller):

    def _call_kw(self, model, method, args, kwargs):
        check_method_name(method)
        return call_kw(request.env[model], method, args, kwargs)

    @route('/api/dataset/call_kw', type='json', auth="machine")
    def call_kw(self, model, method, args, kwargs):
        return self._call_kw(model, method, args, kwargs)
