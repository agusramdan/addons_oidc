# -*- coding: utf-8 -*-
{
    'name': 'Digital Signature',
    'category': 'Tools',
    'description': "This module provides a digital signature feature for the approval process. "
                   "It allows users to sign digitally, ensuring authenticity and "
                   "integrity of the approval process. The digital signature is generated using a "
                   "unique token and can be verified for security purposes.",
    'author': 'Agus Muhammad Ramdan',
    'version': '13.0.0.0.0',
    'depends': ['base', 'web', 'amr_resource', 'auth_jwt'],
    'data': [
        'security/ir.model.access.csv',
        'views/signature_views.xml',
        'views/challenge_views.xml',
        'views/menuitem.xml',
    ],
    'license': 'LGPL-3',
}
