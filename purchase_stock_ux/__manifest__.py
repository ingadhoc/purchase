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
    "name": "Purchase Stock UX",
<<<<<<< 81e024e8e7e4d1bd05d5895f14c0efb99a194566
    "version": "19.0.1.3.0",
||||||| 1afdd564894eaab8763753113a838a40aab49b29
    "version": "18.0.1.2.0",
=======
    "version": "18.0.1.3.0",
>>>>>>> 140e21cd8232eb15f6f445fca077602de9c0bd1b
    "category": "Purchases",
    "sequence": 14,
    "summary": "",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "images": [],
    "depends": [
        "purchase_ux",
        "purchase_stock",
        "stock_ux",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_order_views.xml",
        "views/purchase_line_views.xml",
        "views/stock_move_views.xml",
        "wizards/res_config_settings_views.xml",
        "wizards/purchase_order_cancel_remaining.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": True,
    "application": False,
}
