# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.tools import config

import os
import json

from odoo import tools
from odoo import models

from .providers import (
    ApiKeyProvider,
    BearerProvider,
    BasicProvider,
    ClientSecretProvider,
    ServiceAccountProvider,
)


class ServiceAuthFactory(models.AbstractModel):
    _name = "service.auth.factory"
    _description = "Service Authentication Factory"

    PROVIDERS = {
        "api_key": ApiKeyProvider,
        "bearer": BearerProvider,
        "basic": BasicProvider,
        "client_secret": ClientSecretProvider,
        "service_account": ServiceAccountProvider,
    }

    def create_service_auth(self, credential,):
        auth_type = credential.get("type")
        provider_class = self.PROVIDERS.get(auth_type)
        if not provider_class:
            raise ValueError("Unsupported authentication type: %s ." % auth_type)
        return provider_class(self.env, credential, )
