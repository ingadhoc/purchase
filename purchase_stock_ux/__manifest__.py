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
<<<<<<< cd27a2c78a6de7649e9013cf887b7237f10e9557
    "version": "20.0.1.0.0",
||||||| 7ab2599df8cc5c840623cfd6aab98db5f1ece8f7
    "version": "19.0.1.4.0",
=======
    "version": "19.0.1.4.1",
>>>>>>> f9b3c4ec1195cff017eb7fedcd1f902c725d960d
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
        "security/ir.access.csv",
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
