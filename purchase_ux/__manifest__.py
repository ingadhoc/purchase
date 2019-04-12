##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Purchase UX',
    'version': '11.0.1.4.0',
    'category': 'Purchases',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'purchase',
        # we add stock voucher to have voucher information on purchase line
        'stock_ux',
        # for use user_company_currency_id
        'product_ux',
    ],
    'data': [
        'wizards/purchase_change_currency_views.xml',
        'wizards/purchase_order_line_add_to_invoice_views.xml',
        'views/account_invoice_views.xml',
        'views/ir_ui_menu.xml',
        'views/purchase_order_views.xml',
        'views/purchase_line_views.xml',
        'views/product_template_views.xml',
        'views/stock_move_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
