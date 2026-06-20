# -*- coding: utf-8 -*-

{
    'name': "OIDC",
    'summary': "OIDC, JWT",
    'description': "OIDC, JWT",
    'author': "Agus Muhammad Ramdan",
    'website': "http://www.agusramdan.tech",
    'category': 'API',
    'version': '13.0.0.0.5',
    'depends': ['base', 'web', 'amr_token'],
    'external_dependencies': {
        'python': ['pyjwt', 'cryptography'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/oidc_client_views.xml',
        'views/oidc_authorization_code_views.xml',
        'views/login_template.xml',
        'views/menuitem.xml',

        'wizard/service_account.xml',
    ],
}
