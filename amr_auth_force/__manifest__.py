# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Authentication Force',
    'depends': ['base', 'base_setup', 'auth_oauth' ],
    #'description': < auto-loaded from README file
    'category': 'Tools',
    'version': '16.0.0.0.0',
    'depends': ['base', 'web', 'base_setup', 'auth_oauth'],
    'data': [
        'views/auth_oauth_provider_views.xml',
    ],

    'license': 'LGPL-3',
}
