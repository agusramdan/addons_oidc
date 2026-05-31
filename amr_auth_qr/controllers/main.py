# -*- coding: utf-8 -*-

import logging
import json
import base64

import io
import qrcode

from werkzeug.wrappers import Response

from odoo import api, http, fields
from odoo.http import request
from werkzeug.exceptions import BadRequest, Conflict, NotFound
from werkzeug.utils import redirect
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)



import base64
import json
import secrets
import werkzeug
import qrcode
import logging

from datetime import timedelta
from io import BytesIO

from odoo import http
from odoo.http import request
from odoo.fields import Datetime
from odoo.service import security

from werkzeug import url_encode

_logger = logging.getLogger(__name__)

class MobileController(http.Controller):

    @http.route('/mobile/response',auth='user',website=True,)
    def mobile_sim(self, **kwargs):
        _logger.info(" %s ",kwargs)
        return request.render('amr_auth_qr.mobile_page',kwargs)

    @http.route('/mobile/challenge/<string:jti>', auth='user',type='json',csrf=False,)
    def mobile_load_challenge(self, jti):
        challenge = request.env['auth.challenge'].sudo().search([('jti', '=', jti)], limit=1)

        if not challenge:
            return {
                'success': False,
            }

        return {
            'success': True,
            'challenge': {
                'jti': challenge.jti,
                'action': challenge.action,
                'status': challenge.status,
            }
        }

    @http.route('/mobile/approve/<string:jti>', auth='user', type='json', csrf=False,)
    def mobile_approve(self, jti):

        challenge = request.env['auth.challenge'].sudo().search([('jti', '=', jti), ('status','=','pending')], limit=1)

        if not challenge:
            return {
                'success': False,
            }

        challenge.write({
            'status': 'approved',
            'approved_by': request.env.user.id,
        })

        return {
            'success': True,
        }

    @http.route('/mobile/reject/<string:jti>', auth='user', type='json', csrf=False, )
    def mobile_reject(self, jti):

        challenge = request.env['auth.challenge'].sudo().search([('jti', '=', jti), ('status','=','pending')], limit=1)

        if not challenge:
            return {
                'success': False,
            }

        challenge.write({
            'status': 'rejected',
            'approved_by': request.env.user.id,
        })

        return {
            'success': True,
        }

class QrLoginController(http.Controller):
    @http.route('/qr-<string:action>',auth='public',website=True,)
    def qr_action(self, action,**kwargs):

        token = secrets.token_hex(16)
        nonce = secrets.token_hex(32)

        expired_at = (
            Datetime.now() +
            timedelta(seconds=60)
        )

        challenge = request.env[
            'auth.challenge'
        ].sudo().create({
            'jti': token,
            'nonce': nonce,
            'action': action,
            'status': 'pending',
            'sid': request.session.sid,
            'expired_at': expired_at,
        })
        payload = {
            'jti': challenge.jti,
            'nonce': challenge.nonce,
            'action': challenge.action,
        }
        web_base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = "%s/mobile/response?%s" % (web_base_url, url_encode(payload))
        qr = qrcode.make(url)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return request.render(
            'amr_auth_qr.qr_login_page',
            {
                'challenge': challenge,
                'qr_base64': qr_base64,
            }
        )


    @http.route('/qr-<string:action>/status/<string:token>',auth='public',type='json',csrf=False,)
    def qr_action_status(self, action, token):

        challenge = request.env['auth.challenge'].sudo().search([('jti', '=', token),('action','=',action)], limit=1)

        if not challenge:
            return {
                'success': False,
                'status': 'not_found',
            }

        return {
            'success': True,
            'status': challenge.status,
            'action': challenge.action,
        }

    @http.route('/qr-login/finalize/<string:token>', auth='public',website=True,)
    def qr_login_finalize(self, token, **kwargs):
        challenge = request.env['auth.challenge'].sudo().search([('jti', '=', token)], limit=1)
        if not challenge:
            return request.not_found()

        if challenge.status != 'approved':
            return http.redirect_with_hash('/qr-login')

        if not challenge.approved_by:
            return http.redirect_with_hash('/qr-login')

        # prevent reuse
        if challenge.status == 'used':
            return http.redirect_with_hash('/web/login')
        # IMPORTANT
        if challenge.status == 'approved' and challenge.action == 'login':
            request.env['ir.http'].set_session(challenge.approved_by)
            # invalidate challenge
        challenge.write({'status':'used'})

        return http.redirect_with_hash('/web')
