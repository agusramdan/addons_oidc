# -*- coding: utf-8 -*-
{
    'name': 'Simulasi login ',
    'category': 'Tools',
    'description': "simulasi login dan approval process menggunakan qr. ",
    'author': 'Agus Muhammad Ramdan',
    'version': '13.0.0.0.0',
    'depends': ['base', 'web', ],
    'data': [
        'security/ir.model.access.csv',
        'views/mobile_templates.xml',
        'views/qr_login_templates.xml',
        'views/auth_challenge_views.xml',
    ],
    'license': 'LGPL-3',
}
