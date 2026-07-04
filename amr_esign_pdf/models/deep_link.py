# -*- coding: utf-8 -*-

import json

from odoo import _, api, fields, models


class DeepLink(models.AbstractModel):
    _name = 'deep.link.mixin'
    _description = 'Deep Link Mixin'

    internal_url = fields.Char(
        'Internal URL', compute="_compute_deep_link",
        help="Internal URL for deep link, can be used to identify the document or signature (appearance_text_params)"
    )
    deep_link_hash = fields.Char('Deep Link Hash', readonly=True, )
    deep_link = fields.Char('Deep Link', compute="_compute_deep_link", store=False, )
    deep_link_html = fields.Html(compute='_compute_deep_link', sanitize=False, )
    payload = fields.Char(
        'Payload',
        help="Payload for deep link, can be used to identify the document or signature (appearance_text_params)"
    )

    @api.model
    def get_field_mapping(self):
        return {}

    @api.depends('deep_link_hash')
    def _compute_deep_link(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for rec in self:
            rec.deep_link = f"{base_url}/qr/{rec.deep_link_hash}/{self._name}/{rec.id}"
            rec.deep_link_html = f"""<img src="{rec.deep_link}?view_type=qr" width="250" height="250" />"""
            rec.internal_url = f"{base_url}/web#id={rec.id}&model={self._name}&view_type=form"

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        for vals in vals_list:
            payload = vals.get('payload')
            if payload and isinstance(payload, dict):
                vals['payload'] = json.dumps(payload)

        return super(DeepLink, self).create(vals_list)

    def safe_data_approval_task_line(self, approval_task_line):
        """
        Normalize approval task line values so that they only contain
        fields existing in the target model.

        :param list[dict] approval_task_line:
            Source values.
        :return list[dict]:
            Safe values ready for create().
        """
        target_fields = self._fields
        mapping = self.get_field_mapping() or {}

        result = []

        for vals in approval_task_line:
            if isinstance(vals, models.BaseModel) or not isinstance(vals, dict):
                result.append(vals)
                continue

            safe_vals = {}
            payload = vals.get('payload') or {}
            if isinstance(payload, str):
                payload = json.loads(payload) or {}
            if not isinstance(payload,dict):
                payload = {}

            for field_name, value in vals.items():
                # Field exists on target model
                if field_name in target_fields:
                    safe_vals[field_name] = value
                    continue

                # Try mapping
                mapped_field = mapping.get(field_name)
                if mapped_field and mapped_field in target_fields:
                    safe_vals[mapped_field] = value
                    continue
                payload[field_name] = value
            vals['payload'] = payload
            result.append(safe_vals)

        return result

    def ensure_create_dict(self, vals):
        if isinstance(vals, models.BaseModel):
            return vals

        if not isinstance(vals, dict):
            raise ValueError("vals must be dict or recordset")
        vals = self.prepare_create_vals(self.env[self._name],vals)
        return self.create(vals)

    def prepare_create_vals(self, model, vals):
        vals = vals.copy()

        _fields = model._fields
        for field_name, value in list(vals.items()):
            field = _fields.get(field_name)

            if not field:
                continue

            # One2many
            if field.type == 'one2many':
                commands = []

                for line in value or []:
                    if isinstance(line, models.BaseModel):
                        commands.append((4, line.id))
                    elif isinstance(line, dict):
                        commands.append((0, 0, self.prepare_create_vals(
                            self.env[field.comodel_name],
                            line
                        )))

                vals[field_name] = commands

            # Many2one
            elif field.type == 'many2one':
                if isinstance(value, models.BaseModel):
                    vals[field_name] = value.id

            # Many2many
            elif field.type == 'many2many':
                ids = []
                for rec in value or []:
                    if isinstance(rec, models.BaseModel):
                        ids.append(rec.id)
                    elif isinstance(rec, int):
                        ids.append(rec)
                vals[field_name] = [(6, 0, ids)]

        return vals
