# -*- coding: utf-8 -*-

{
    'name': "OIDC",
    'summary': """
        OIDC,
        JWT,
        Sharing Trusted Token Authentication between Applications Server
    """,
    'description': """
        OIDC,
        JWT,
        Sharing Trusted Token Authentication between Applications Server
    """,
    'author': "Agus Muhammad Ramdan",
    'website': "http://www.agusramdan.tech",
    'category': 'API',
    'version': '13.0.0.0.0',
    'depends': ['base', 'web', 'amr_token'],
    'external_dependencies': {
        'python': ['pyjwt'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/oidc_client_views.xml',
        'views/oidc_authorization_code_views.xml',
        'views/login_template.xml',
    ],
}
