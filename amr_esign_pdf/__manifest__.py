{
    'name': 'ESign PDF',
    'version': '13.0.1.0.0',
    'category': 'Tools',
    'summary': 'Manage PAdES multiple signature PDF workflow in Odoo 13.',
    'description': 'Support PDF document preparation, CMS request, and multiple signature workflow for Odoo 13.',
    'author': 'Auto Generated',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', ],
    'data': [
        'security/ir.model.access.csv',

        'views/pdf_document_views.xml',
        'views/pdf_sign_views.xml',
        'views/user_ca_data_views.xml',

        'wizard/user_ca_data_wizard.xml',

        'views/menuitems.xml',
    ],
    'demo': [],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'application': False,
    'external_dependencies': {
        'python': ['pyhanko', 'PyMuPDF', 'pyhanko-certvalidator', 'cryptography']
    },
}
