# -*- coding: utf-8 -*-

{
    'name': 'Authentication Force',
    'depends': ['base', 'base_setup', 'auth_oauth' ],
    #'description': < auto-loaded from README file
    'category': 'Tools',
    'version': '13.0.1.0.0',
    'depends': ['base', 'web', 'base_setup', 'auth_oauth'],
    'data': [
        'views/auth_oauth_provider_views.xml',
    ],

    'license': 'LGPL-3',
}
