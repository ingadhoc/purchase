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
    'name': 'Purchase Usability Improvements',
    'version': '9.0.1.17.0',
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
        # we add stock voucher to hav voucher information on purchase line
        'stock_voucher',
        'stock_usability',
    ],
    'data': [
        'wizard/purchase_change_currency_view.xml',
        'wizard/purchase_order_line_add_to_invoice_view.xml',
        'views/account_invoice_view.xml',
        'views/purchase_view.xml',
        'views/purchase_order_view.xml',
        'views/purchase_line_view.xml',
        'views/stock_move_view.xml',
    ],
    'demo': [
    ],
    'installable': False,
    'auto_install': False,
    'application': False,
}
