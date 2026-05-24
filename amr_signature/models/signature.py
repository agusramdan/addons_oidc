import uuid
import hashlib
from psycopg2 import IntegrityError
from odoo import api, fields, models
from odoo.exceptions import UserError


class ApprovalSignature(models.Model):
    _name = 'amr.signature'
    _description = 'Digital Approval Signature'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(readonly=1)
    issuer_url = fields.Char(readonly=1)
    audience = fields.Char(readonly=1)
    jwt_token = fields.Text("Token")
    signature = fields.Char(readonly=1)
    hash_from = fields.Char(readonly=1)
    deep_link = fields.Char(compute="compute_deeplink")
    qr_signature = fields.Char(compute="compute_deeplink")
    qr_signature_html = fields.Html(
        compute='compute_deeplink',
        sanitize=False
    )
    _sql_constraints = [
        (
            'name_unique',
            'unique(name)',
            'name already exists'
        )
    ]

    @api.model
    def create_with_retry(self, jwt_token):
        if self.search([('jwt_token', '=', jwt_token)]):
            raise IntegrityError("Token Duplicate")
        path = jwt_token.split('.')
        signature = path[2]
        result = self.env["amr.resource.helper"].validate(jwt_token)
        if not result:
            raise ValueError

        issuer_url = result['iss']
        audience = result['aud']
        if isinstance(audience, list):
            audience = " ".join(audience)
        vals = {
            'issuer_url': issuer_url,
            'audience': audience,
            'signature': signature,
            'jwt_token': jwt_token,
        }
        signature = vals['signature']
        hash_from = "signature-md5-%s"
        for i in range(10):
            name = hashlib.md5(signature.encode()).hexdigest()
            try:
                vals['name'] = name
                vals['hash_from'] = hash_from % i
                return self.create(vals)
            except IntegrityError:
                self.env.cr.rollback()
            signature = name
        raise Exception(
            'Cannot generate unique deep link'
        )

    @api.depends('name')
    def compute_deeplink(self):
        for rec in self:
            rec.deep_link = rec.get_base_url() + "/dl/" + rec.name
            rec.qr_signature = rec.get_base_url() + "/qr/" + rec.name
            rec.qr_signature_html = f"""
                            <img
                                src="{rec.qr_signature}"
                                width="250"
                                height="250"
                            />
                        """
