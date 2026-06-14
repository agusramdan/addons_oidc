{
    'name': 'OIDC Client',
    'category': 'Tools',
    'author': 'Agus Muhammad Ramdan',
    'version': '13.0.0.0.1',
    'depends': ['base', 'web', 'base_setup', 'amr_resource'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',

        'views/service_endpoint_views.xml',
        'views/service_credential_views.xml',
        'views/menuitem.xml',

        'wizards/service_credential.xml',
        'wizards/service_endpoint_test.xml',
    ],
}
