# -*- coding: utf-8 -*-

{
    'name': "Token Provider",
    'summary': "Token Provider",
    'description': "Token Provider",
    'author': "Agus Muhammad Ramdan",
    'website': "http://www.agusramdan.tech",
    'category': 'API',
    'version': '13.0.0.0.6',
    'depends': ['base', 'base_setup', 'web', 'amr_resource'],
    'external_dependencies': {
        'python': ['pyjwt'],
    },
    'data': [
        'security/ir.model.access.csv',

        'views/public_key_views.xml',
        'views/menuitem.xml',
        'views/res_config_settings_views.xml',
    ],
}
