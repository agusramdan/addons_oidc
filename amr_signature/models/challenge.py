# -*- coding: utf-8 -*-

import logging
import jwt
import datetime
import uuid
from jwt import InvalidTokenError
from odoo import api, fields, models
from odoo.http import request
from odoo import models, fields
from odoo.addons.amr_resource.exceptions import APIException

_logger = logging.getLogger(__name__)


class Challenge(models.Model):
    _name = "amr.challenge"
    _description = "Generic Signed Action Challenge"
    _rec_name = "jti"

    sid = fields.Char(index=True)  # session/browser/device context
    jti = fields.Char(index=True, required=True)
    nonce = fields.Char(required=True)
    action_type = fields.Selection([
        ('login', 'Login'),
        ('approval', 'Approval'),
        ('sign', 'Digital Signature'),
        ('device', 'Device Binding'),
    ], required=True, index=True)
    jwt_token = fields.Text("Token")
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired')
    ], default='pending', index=True)
    user_id = fields.Many2one('res.users')
    expires_at = fields.Datetime(required=True)
    res_model = fields.Char()
    device_id = fields.Char()
    signature = fields.Text()  # optional store JWS (kalau mau audit)
    create_date = fields.Datetime()
    deep_link = fields.Char(compute="compute_deeplink")
    qr_challenge = fields.Char(compute="compute_deeplink")
    qr_challenge_html = fields.Html(
        compute='compute_deeplink',
        sanitize=False
    )

    @api.depends('jti')
    def compute_deeplink(self):
        for rec in self:
            rec.deep_link = rec.get_base_url() + "/cl/dl/" + rec.jti
            rec.qr_challenge = rec.get_base_url() + "/cl/qr/" + rec.jti
            rec.qr_challenge_html = f"""
                                <img
                                    src="{rec.qr_challenge}"
                                    width="250"
                                    height="250"
                                />
                            """

    def create_challenge(self, action_type=None, res_model=None, device_id=None, sid=None, **kwargs):
        # -----------------------------
        # 1. Generate identifiers
        # -----------------------------
        jti = str(uuid.uuid4())
        nonce = str(uuid.uuid4())[:12]
        expires_at = fields.Datetime.now() + datetime.timedelta(seconds=60)

        # -----------------------------
        # 2. Create challenge record
        # -----------------------------

        challenge = self.create([{
            'sid': sid,
            'jti': jti,
            'nonce': nonce,
            'action_type': action_type,
            'res_model': res_model,
            'device_id': device_id,
            'expires_at': expires_at,
            'state': 'pending',
        }])[0]

        challenge.write({
            'jwt_token': challenge.encode(challenge.get_payload())
        })
        return challenge

    def get_payload(self):
        payload = {
            "jti": self.jti,
            "nonce": self.nonce,
            "sid": self.sid,
            "action_type": self.action_type,
            "exp": int(self.expires_at.timestamp())
        }
        if self.device_id:
            payload['device_id'] = self.device_id
        if self.res_model:
            payload['res_model'] = self.res_model

        return payload

    def encode(self):
        # "iss": "odoo-auth",
        # "aud": "odoo-mobile",
        payload = self.get_payload()
        token, payload = self.env['amr.resource.helper'].encode(**payload)
        return token, payload

    def decode(self, token, **kwargs):
        # decision = kwargs.get('decision')
        # device_id = kwargs.get('device_id')
        if not token:
            raise APIException("missing_jws")

        # -----------------------------
        # 1. Load public key
        # 2. Verify JWS signature
        if self.user_id:
            payload = self.user_id.decode(token, **kwargs)
        else:
            payload = self.env['amr.resource.helper'].decode(token, **kwargs)

        return payload

    def process(self, **kwargs):

        jws = kwargs.pop('jws', None)
        decision = kwargs.get('decision')
        device_id = kwargs.get('device_id')

        if not jws:
            raise APIException("missing_jws")
        payload = jwt.decode(jws, options={"verify_signature": False})
        # -----------------------------
        # 1. Load public key
        # -----------------------------
        # public_key = request.env['ir.config_parameter'].sudo().get_param('auth.public_key')
        #
        # try:
        #     # -----------------------------
        #     # 2. Verify JWS signature
        #     # -----------------------------
        #     payload = jwt.decode(
        #         jws,
        #         public_key,
        #         algorithms=["ES256"],
        #         audience="odoo-mobile"
        #     )
        #
        # except Exception as e:
        #     return {"error": "invalid_signature", "detail": str(e)}

        jti = payload.get("jti")
        # nonce = payload.get("nonce")
        # sid = payload.get("sid")
        action_type = payload.get("action_type")

        # -----------------------------
        # 3. Find challenge
        # -----------------------------
        challenge = self.sudo().search([
            ('jti', '=', jti),
            ('state', '=', 'pending')
        ], limit=1)

        if not challenge:
            return APIException("challenge_not_found_or_used")

        # -----------------------------
        # 4. Expiration check
        # -----------------------------
        if challenge.expires_at < fields.Datetime.now():
            challenge.state = 'expired'
            raise APIException("challenge_expired")

            # -----------------------------
        # 5. Device binding check (optional)
        # -----------------------------
        if challenge.device_id and device_id and challenge.device_id != device_id:
            raise APIException("device_mismatch")

        payload = challenge.decode(jws, **kwargs)

        # -----------------------------
        # 6. Decision handling
        # -----------------------------
        if decision != "approve":
            challenge.state = "rejected"
            return {
                "status": "ok",
                "result": "rejected"
            }

        # -----------------------------
        # 7. Approve challenge
        # -----------------------------
        challenge.state = "approved"
        challenge.user_id = request.env.user.id
        challenge.device_id = device_id

        # -----------------------------
        # 8. Execute action
        # -----------------------------
        result = self._execute_action(challenge, payload)
        challenge.write({
            "signature": jws
        })
        return {
            "status": "ok",
            "challenge_id": challenge.id,
            "action_type": action_type,
            "result": "approved",
            "execution_result": result
        }

    def _execute_action(self, challenge, payload):

        # -------------------------------------------------
        # ACTION EXECUTOR (core logic)
        # -------------------------------------------------
        action_type = payload.get("action_type")

        # -------------------------
        # LOGIN FLOW
        # -------------------------
        if action_type == "login":
            request.session.uid = challenge.user_id.id
            return {"login": "success"}

        # -------------------------
        # APPROVAL FLOW (Odoo record)
        # -------------------------
        if action_type == "approval":
            model = payload.get("res_model")
            res_id = payload.get("res_id")

            if model and res_id:
                record = request.env[model].sudo().browse(int(res_id))

                # contoh generic approval method
                if hasattr(record, "action_approve"):
                    record.action_approve()
                elif hasattr(record, "approve"):
                    record.approve()
                else:
                    record.write({"state": "approved"})

                return {"approved_record": True}

        # -------------------------
        # SIGN FLOW (future use)
        # -------------------------
        if action_type == "sign":
            return {"signed": True}

        return {"result": "unknown_action"}
