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

from datetime import timedelta
from io import BytesIO

import qrcode

from odoo import http
from odoo.http import request
from odoo.fields import Datetime
from odoo.service import security

def set_session(user, session_token=None):
    session = request.session
    session.rotate = True
    session.uid = user.id
    session.login = user.login
    if user:
        session.session_token = security.compute_session_token(session, request.env)
    else:
        session.session_token = session_token
    if not session.session_token:
        request.uid = None
        session.uid = None
        session.login = None
    else:
        request.uid = user.id
        request.disable_db = False
        session.get_context()

class QrLoginController(http.Controller):

    @http.route(
        '/mobile-sim',
        auth='user',
        website=True,
    )
    def mobile_sim(self, **kwargs):

        return request.render(
            'auth_qr_mobile_sim.mobile_sim_page'
        )

    @http.route(
        '/mobile-sim/challenge/<string:token>',
        auth='user',
        type='json',
        csrf=False,
    )
    def mobile_load_challenge(self, token):

        challenge = request.env[
            'auth.challenge'
        ].sudo().search([
            ('challenge_token', '=', token)
        ], limit=1)

        if not challenge:
            return {
                'success': False,
            }

        return {
            'success': True,
            'challenge': {
                'token': challenge.challenge_token,
                'action': challenge.action,
                'status': challenge.status,
            }
        }

    @http.route(
        '/mobile-sim/approve/<string:token>',
        auth='user',
        type='json',
        csrf=False,
    )
    def mobile_approve(self, token):

        challenge = request.env[
            'auth.challenge'
        ].sudo().search([
            ('challenge_token', '=', token)
        ], limit=1)

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

    @http.route(
        '/qr-login',
        auth='public',
        website=True,
    )
    def qr_login(self, **kwargs):

        token = secrets.token_hex(16)

        nonce = secrets.token_hex(32)

        expired_at = (
            Datetime.now() +
            timedelta(seconds=60)
        )

        challenge = request.env[
            'auth.challenge'
        ].sudo().create({
            'challenge_token': token,
            'nonce': nonce,
            'action': 'login',
            'status': 'pending',
            'session_sid': request.session.sid,
            'expired_at': expired_at,
        })

        payload = {
            'challenge_token': challenge.challenge_token,
            'nonce': challenge.nonce,
            'action': challenge.action,
        }

        qr = qrcode.make(
            json.dumps(payload)
        )

        buffer = BytesIO()

        qr.save(buffer, format='PNG')

        qr_base64 = base64.b64encode(
            buffer.getvalue()
        ).decode()

        return request.render(
            'auth_qr_mobile_sim.qr_login_page',
            {
                'challenge': challenge,
                'qr_base64': qr_base64,
            }
        )


    @http.route(
        '/qr-login/status/<string:token>',
        auth='public',
        type='json',
        csrf=False,
    )
    def qr_login_status(self, token):

        challenge = request.env[
            'auth.challenge'
        ].sudo().search([
            ('challenge_token', '=', token)
        ], limit=1)

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

    @http.route(
        '/qr-login/finalize/<string:token>',
        auth='public',
        website=True,
    )
    def qr_login_finalize(self, token, **kwargs):

        challenge = request.env[
            'auth.challenge'
        ].sudo().search([
            ('challenge_token', '=', token)
        ], limit=1)

        if not challenge:
            return request.not_found()

        if challenge.status != 'approved':
            return request.redirect('/qr-login')

        if not challenge.approved_by:
            return request.redirect('/qr-login')

        # prevent reuse
        if challenge.status == 'used':
            return request.redirect('/web/login')
        # IMPORTANT
        set_session(challenge.approved_by)

        # invalidate challenge
        challenge.action_archive()

        return http.redirect_with_hash('/web')
