# -*- coding: utf-8 -*-

{
    'name': 'ESign PDF',
    'version': '13.0.1.0.1',
    'category': 'Tools',
    'summary': 'Manage PAdES multiple signature PDF workflow in Odoo 13.',
    'description': 'Support PDF document preparation, CMS request, and multiple signature workflow for Odoo 13.',
    'author': 'Agus Muhammad Ramdan',
    'website': 'https://agus.ramdan.tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/base_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',

        'views/pdf_document_views.xml',
        'views/pdf_sign_views.xml',
        'views/pdf_sign_template_views.xml',
        'views/user_ca_data_views.xml',
        'views/res_users_views.xml',

        'wizard/user_ca_data_wizard.xml',
        'wizard/sign_ca_select_wizard.xml',
        'wizard/pdf_verify_wizard.xml',
        'views/menuitems.xml',
        'views/pdf_document_demo_views.xml',
    ],
    'demo': [],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'application': True,
    'external_dependencies': {
        'python': ['pyhanko', 'PyMuPDF', 'pyhanko-certvalidator', 'cryptography']
    },
}
