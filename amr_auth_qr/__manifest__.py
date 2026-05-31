# -*- coding: utf-8 -*-
{
    'name': 'QR Auth',
    'category': 'Tools',
    'description': "login dan approval process menggunakan qr. ",
    'author': 'Agus Muhammad Ramdan',
    'version': '13.0.0.0.0',
    'depends': ['base', 'web', 'amr_resource'],
    'data': [
        'security/ir.model.access.csv',
        'views/mobile_templates.xml',
        'views/qr_login_templates.xml',
        'views/auth_challenge_views.xml',
    ],
    'license': 'LGPL-3',
}
