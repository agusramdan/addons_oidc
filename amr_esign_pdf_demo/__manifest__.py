# -*- coding: utf-8 -*-

{
    'name': 'ESign Demo PDF',
    'version': '13.0.1.0.1',
    'category': 'Tools',
    'summary': 'Demo Approval  Odoo 13.',
    'description': 'Demo Approval is PDF Sign.',
    'author': 'Auto Generated',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'amr_esign_pdf', 'amr_approval'],
    'data': [
        'data/approval_document_data.xml',
        'reports/approval.xml',
        'views/menuitems.xml',
        'data/approval_template_data.xml',
    ],
    'demo': [],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'application': False,
}
