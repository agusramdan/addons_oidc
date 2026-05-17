# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'OAuth2 Authentication : Custom',
    'category': 'Tools',
    'description': """
Allow users to login through OAuth2 Provider.
=============================================
""",
    'maintainer': 'Agus Muhammad Ramdan',
    'depends': ['base', 'web', 'base_setup', 'amr_token', 'amr_oauth'],
    'data': [
        'security/ir.model.access.csv',

        'views/trust_audience_views.xml',
    ],
    'license': 'LGPL-3',
}
