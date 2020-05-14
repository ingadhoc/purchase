# © 2015-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Purchase Suggest',
    'version': '13.0.1.0.0',
    'category': 'Purchase',
    'license': 'AGPL-3',
    'summary': 'Suggest POs from special suggest orderpoints',
    'author': 'Akretion,ADHOC SA',
    'website': 'http://www.akretion.com',
    'depends': [
        'purchase_stock_ux',
        # 'purchase_suggest',
        'product_replenishment_cost',
    ],
    'conflicts': ['procurement_suggest'],
    'data': [
        'views/stock_view.xml',
        'wizard/purchase_suggest_view.xml',
    ],
    'installable': True,
}
