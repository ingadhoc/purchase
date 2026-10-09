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
    "name": "Purchase UX",
    "version": "19.0.1.11.0",
    "category": "Purchases",
    "sequence": 14,
    "summary": "Purchase order improvements: currency change, price updates, invoice controls and menu enhancements",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "images": [],
    "depends": [
        "purchase",
        "account_ux",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_actions_report_data.xml",
        "wizards/purchase_change_currency_views.xml",
        "wizards/purchase_order_line_add_to_invoice_views.xml",
        "views/account_move_views.xml",
        "views/ir_ui_menu.xml",
        "views/purchase_order_views.xml",
        "views/purchase_line_views.xml",
        "views/product_template_views.xml",
        "views/product_supplierinfo_views.xml",
        "views/res_config_settings_views.xml",
        "views/purchase_bill_line_match_views.xml",
    ],
    "demo": [
        "demo/purchase_order_demo.xml",
    ],
<<<<<<< 4026f2cf5b296579ab4dd7a384f99ef3fc503d56
    "installable": False,
||||||| 28154baa3c011c4fc757ef6d8c9f5887e314e43a
    "installable": True,
=======
    "assets": {
        "web.assets_backend": [
            "purchase_ux/static/src/views/purchase_dashboard.xml",
        ],
    },
    "installable": True,
>>>>>>> d0e4f07197e71bb518c8fea06a046b71bdbcae1b
    "auto_install": False,
    "application": False,
}
