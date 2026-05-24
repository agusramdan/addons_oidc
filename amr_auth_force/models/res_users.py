# -*- coding: utf-8 -*-

import logging

from odoo import api, models
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo import api, fields, models, tools, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @classmethod
    def _login(cls, db, login, password):
        if not password:
            raise AccessDenied()

        # user_agent_env['login'] = login
        oauth_provider_force = request.env['auth.oauth.provider'].sudo().search([('force_login', '=', True)])
        if not request.params.get('admin_login') and oauth_provider_force:
            # self = request.env['res.users'].sudo()
            # user = self.search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
            # if not user:
            #     raise AccessDenied()
            for oauth_provider in oauth_provider_force:
                try:
                    result = oauth_provider.auth_token_rpc(login, password)
                    access_token = result.get('access_token')
                    validation = oauth_provider.auth_oauth_validate(access_token)
                    user = oauth_provider.get_email_user_match(validation)
                    _logger.info("User %s ", user)
                    if user:
                        # user = self.search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
                        user.write({
                            'oauth_provider_id': oauth_provider.id,
                            'oauth_access_token': result.get('access_token')
                        })
                        user._update_last_login()
                        return user.id
                except:
                    _logger.exception("error")
                    continue
            user = request.env['res.users'].sudo().get_user_by_username(login)
            if not (user._rpc_api_keys_only() or user.id in [1, 2] or user.user_has_groups('base.group_erp_manager')):
                _logger.info("Force Login to OIDC Provider.")
                raise AccessDenied()
            try:
                return super(ResUsers, cls)._login(db, login, password, user_agent_env=user_agent_env)
            except AccessDenied:
                _logger.info("Fallback to OIDC Provider Login.")
                for oauth_provider in oauth_provider_force:
                    try:
                        result = oauth_provider.auth_token_rpc(login, password)
                        access_token = result.get('access_token')
                        validation = oauth_provider.auth_oauth_validate(access_token)
                        user = oauth_provider.get_email_user_match(validation)
                        _logger.info("User %s ", user)
                        if user:
                            user.write({
                                'oauth_provider_id': oauth_provider.id,
                                'oauth_access_token': result.get('access_token')
                            })
                            user._update_last_login()
                            return user.id
                    except:
                        _logger.exception("error")
                        continue

        #return super(ResUsers, cls)._login(db, login, password, user_agent_env=user_agent_env)

    # def _check_credentials(self, password, user_agent_env):
    #     if self.env['auth.oauth.provider'].sudo().search([('force_login', '=', True)]):
    #         raise AccessDenied()
    #
    #     return super(ResUsers, self)._check_credentials( password, user_agent_env=user_agent_env)
    def get_user_by_username(self, login):
        return self.search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
    # @api.model
    # def _get_login_domain(self, login):
    #     return ['|',('login', '=', login),('email', '=', login)]
