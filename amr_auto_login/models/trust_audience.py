# -*- coding: utf-8 -*-

import logging
import jwt

from odoo import models, fields
from jwt import InvalidTokenError, InvalidAudienceError, InvalidIssuerError

_logger = logging.getLogger(__name__)


class TrustAudience(models.Model):
    _name = 'trust.audience'
    _description = 'Trust Audience'
    _order = 'name'

    name = fields.Char('Name', required=True, help='Nmae')
    _sql_constraints = [
        (
            'audience_unique',
            'unique(name)',
            'Audience must be unique.'
        )
    ]
    issuer_ids = fields.Many2many(
        'auth.oauth.provider',
        'trust_audience_provider_issuer_ids_rel',
        string='Issuers'
    )

    def get_token_audience(self, audience, issuer):
        _logger.info("audience %s , issuer %s", audience, issuer)
        audience_id = self.sudo().search([('name', '=', audience)], limit=1)
        for issuer_id in audience_id.issuer_ids:
            if issuer_id.issuer_url == issuer:
                return audience_id, issuer_id

        return None, None

    def validate(self, token, raise_exception=False, check_internal_user=True):
        payload = {}
        try:
            payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": True,
                    "verify_aud": False,
                    "verify_iss": False,
                }
            )
            audience, issuer = self.get_token_audience(payload.get('aud'), payload.get('iss'))
            if not audience:
                _logger.error(f"Invalid Audience {audience}")
                raise InvalidAudienceError('Invalid Audience')
            if not issuer:
                _logger.error(f"Invalid Issuer {issuer}")
                raise InvalidIssuerError('Invalid Issuer')
            if not issuer.validate(token):
                raise InvalidIssuerError('Invalid Issuer Check Token')
            return self.check_internal_user(payload) if check_internal_user else payload
        except InvalidTokenError:
            _logger.exception("InvalidTokenError")
            if raise_exception:
                raise
        return payload

    def check_internal_user(self, payload):
        login = payload.get('sub')
        email = payload.get('email')
        user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
        if not user:
            user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
        if not user:
            user = self.env['res.users'].sudo().search([('email', '=', email)], limit=1)
        if not user:
            user = self.env['res.users'].sudo().search([('partner_id.email', '=', email)], limit=1)
        if user:
            payload['uid'] = user.id
            payload['username'] = user.login
            payload['have_internal_user'] = True
            return payload
        else:
            payload['have_internal_user'] = False

        _logger.error(f"User Not found {login} , {email}")
        return payload
