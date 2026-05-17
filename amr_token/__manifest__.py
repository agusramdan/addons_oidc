# -*- coding: utf-8 -*-

{
    'name': "JWT Token",
    'summary': """
        JWT Token,
        Sharing Trusted Token Authentication between Applications Server
    """,
    'description': """
        JWT Token,
        Sharing Trusted Token Authentication between Applications Server
    """,
    'author': "Agus Muhammad Ramdan",
    'website': "http://www.agusramdan.tech",
    'category': 'API',
    'version': '13.0.0.0.0',
    'depends': ['base', 'base_setup', 'web', ],
    'external_dependencies': {
        'python': ['pyjwt'],
    },
    'data': [
        'security/ir.model.access.csv',

        'views/token_views.xml',

        'views/res_config_settings_views.xml',
    ],
}
