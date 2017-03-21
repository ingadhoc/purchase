# -*- coding: utf-8 -*-
# © 2015-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Purchase Suggest',
    'version': '9.0.1.3.0',
    'category': 'Purchase',
    'license': 'AGPL-3',
    'summary': 'Suggest POs from special suggest orderpoints',
    'author': 'Akretion,ADHOCSA',
    'website': 'http://www.akretion.com',
    'depends': [
        'purchase',
        'product_supplier_search',
        # 'purchase_suggest',
        'stock_usability',
        'product_replenishment_cost',
    ],
    'conflicts': ['procurement_suggest'],
    'data': [
        'stock_view.xml',
        'wizard/purchase_suggest_view.xml',
    ],
    'installable': True,
}
