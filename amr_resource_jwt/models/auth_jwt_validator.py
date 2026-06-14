# Copyright 2021 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from functools import partial

import jwt  # pylint: disable=missing-manifest-dependency
from jwt import PyJWKClient
from werkzeug.exceptions import InternalServerError

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError

from odoo.addons.auth_jwt.exceptions import (
    AmbiguousJwtValidator,
    JwtValidatorNotFound,
    UnauthorizedInvalidToken,
    UnauthorizedPartnerNotFound,
)

_logger = logging.getLogger(__name__)


class AuthJwtValidator(models.Model):
    _inherit = "auth.jwt.validator"

    user_id_strategy = fields.Selection(
        selection_add=[('user_match', 'User Match')]
    )

    def _get_uid(self, payload):
        if self.user_id_strategy == 'user_match':
            user = self.env['amr.resource.helper'].get_user_match(payload)
            if user:
                return user.id
        return super()._get_uid(payload)

    @api.model
    def get_validator(self, validator_name, issuer, algorithm):
        validator = self.search([
            ('signature_type', '=', 'public_key'),
            ('public_key_algorithm', '=', algorithm)
        ])
        if len(validator) != 1:
            _logger.error(
                "More than one JWT validator found for name %r", validator_name
            )
            raise AmbiguousJwtValidator()
        return validator

    @api.model
    def decode(self, token):
        header = jwt.get_unverified_header(token)
        algorithm = header.get('alg')
        if algorithm.startswith('HS'):
            domain = [
                ('signature_type', '=', 'secret'),
                ('secret_algorithm', '=', algorithm)
            ]
        else:
            domain = [
                ('signature_type', '=', 'public_key'),
                ('public_key_algorithm', '=', algorithm)
            ]
        payload = jwt.decode(
            token,
            options={
                "verify_signature": False
            }
        )
        issuer = payload.get('iss')
        domain.append(('issuer', '=', issuer))
        records = self.sudo().search(domain)
        for rec in records:
            try:
                payload = rec._decode(token)
                payload['kid'] = header.get('kid')
                payload['alg'] = algorithm
                return payload
            except:
                pass
        raise UnauthorizedInvalidToken()
