# -*- coding: utf-8 -*-

import logging
import json

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
        """ retrieve and sign in the user corresponding to provider and validated access token
            :param provider: oauth provider id (int)
            :param validation: result of validation of access token (dict)
            :param params: oauth parameters (dict)
            :return: user login (str)
            :raise: AccessDenied if signin failed

            This method can be overridden to add alternative signin methods.
        """
        oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        user = oauth_provider.get_user_match(validation)
        if user:
            _logger.info("found user %s for provider %s", user.login, oauth_provider.name)
            # hack here to update access token on each login, in case it has changed since last login
            user.write({
                'oauth_provider_id': provider,
                'oauth_uid': validation['user_id'],
                'oauth_access_token': params['access_token']})
            return user.login

        return super(ResUsers, self)._auth_oauth_signin(provider, validation, params)
