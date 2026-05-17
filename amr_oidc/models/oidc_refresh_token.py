# -*- coding: utf-8 -*-

import jwt
import time
import logging
import uuid

from datetime import datetime, timedelta
from jwt import InvalidTokenError
from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class AccessToken(models.Model):
    _name = 'oidc.refresh.token'
    _description = "JWT Refresh Token"

    @api.model
    def get_expires_in(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('amr_token.expires_in')) or (60 * 60 * 24)

    @api.model
    def get_secret(self):
        return self.env['ir.config_parameter'].sudo().get_param('amr_token.secret')

    @api.model
    def get_issuer(self):
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')

    @api.model
    def get_algorithm(self):
        return 'HS256'

    token = fields.Char(required=True, index=True)
    user_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="cascade"
    )
    expires_at = fields.Datetime(required=True)
    revoked = fields.Boolean(default=False)

    _sql_constraints = [
        ("token_unique", "unique(token)", "Refresh token must be unique")
    ]

    @staticmethod
    def generate_token():
        return str(uuid.uuid4())

    def create_refresh_token(self, user):
        token = self.generate_token()
        expires_in = (60 * 60 * 24*14)
        expire = int(time.time()) + expires_in
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        self.create({
            "token": token,
            "user_id": user.id,
            "expires_at": expires_at,
        })
        payload = {
            'token': token,
            'data': f"{user.id}-{user.email}-{time.time()}-{self.env.cr.dbname}",
            'aud': self.get_audience(),
            'iss': self.get_issuer(),
            'exp': expire
        }
        return jwt.encode(
            payload,
            self.get_secret(),
            algorithm=self.get_algorithm()
        )

    def validate_token(self, token, audience):
        try:
            payload = jwt.decode(
                token,
                self.get_secret(),
                issuer=self.get_issuer(),
                audience=audience,
                algorithms=[self.get_algorithm()],
                options={
                    "require": ["exp", "iss", "aud"]
                }
            )
            if not payload.get("token"):
                rec = self.sudo().search(
                    [("token", "=", payload.get("token")),
                     ("revoked", "=", False),
                     ('expires_at','<',fields.Datetime.now())],
                    limit=1
                )
                if not rec or rec.expires_at < fields.Datetime.now():
                    return payload
        # except InvalidIssuerError:
        #     pass
        # except InvalidAudienceError:
        #     pass
        # except ExpiredSignatureError:
        #     pass
        except InvalidTokenError:
            pass
        return None