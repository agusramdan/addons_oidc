# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _auth_oauth_validate(self, provider, access_token):
        """ return the validation data corresponding to the access token """
        oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        return oauth_provider.auth_oauth_validate(access_token)

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        oauth_uid = validation['user_id']
        records = self.env['res.users'].with_context(
            active_test=False
        ).search([('oauth_provider_id', '=', provider), ('oauth_uid', '=', oauth_uid)], limit=1)
        not records.active and records.action_unarchive()
        login = super(ResUsers, self)._auth_oauth_signin(provider, validation, params)
        oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        user = self.search([('login', '=', login)], limit=1)
        if user:
            self._apply_provider_groups(user, oauth_provider, )
        return login

    @api.model
    def _apply_provider_groups(self, user, provider):
        admin_group = self.env.ref('base.group_erp_manager')
        internal_group = self.env.ref('base.group_user')
        portal_group = self.env.ref('base.group_portal')
        if provider.user_type == 'admin':
            user.write({
                'groups_id': [
                    (3, portal_group.id),
                    (4, admin_group.id),
                ]
            })
        elif provider.user_type == 'internal':
            user.write({
                'groups_id': [
                    (3, portal_group.id),
                    (4, internal_group.id),
                ]
            })
