.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===========
Purchase UX
===========

This module provides several improvements and enhancements to the standard Odoo purchase workflow, making it more user-friendly and feature-rich.

Features
========

Purchase Orders
---------------

* Hide purchase quotations menu for cleaner navigation
* Show all purchase records (quotations and confirmed orders) in unified menu
* Add "Force Invoice Status" button (admin only with technical features)
* Add "Change Currency" button to update order line prices
* Add "Update Prices" button to refresh prices from supplier
* Add "Update Supplier Prices" button to update/create supplier pricelists
* Include internal notes field for better documentation

Purchase Order Lines
--------------------

* Prevent automatic price recalculation when quantity changes
* Use product standard price when supplier price is not available (seller price = 0.0)
* Enhanced invoice quantity management and controls


Installation
============

1. Install this module through Odoo Apps or manually
2. No additional dependencies required beyond standard Odoo

Configuration
=============

No special configuration is required. All features are available immediately after installation.

Usage
=====

Purchase Invoices
-----------------

* Use **Update Supplier Prices** button to update supplier pricelists from invoice data

Products
--------

* Search products by supplier using the enhanced search filters
* Group products by main supplier in list views

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/purchase/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* |company| |icon|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
