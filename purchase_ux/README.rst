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

Several Improvements to purchases

On purchase orders:

#. Make button send by email also available on done state on purchase orders
#. Odoo consider that a purchase order on done state has nothing to be invoiced, we change that behaviour to keep it as on sale orders
#. Make purchase quotations menu only visible with technical features
#. Make purchase orders menu show all purchase records (quotations, and confirmed ones)
#. Add delivery status on purchases
#. Add print PO on purchase and done status
#. Add button to force "invoiced" only for admin with tec features
#. Add button to change the currency and update the prices of the order lines
#. Add a to filter by PO with billable returns.
#. Add link from invoices to the purchase orders that generate it.
#. Add a button "Update Supplier Prices" to update (or create prices) for this provider and all products loaded on the order.
#. Add a button "Update Prices" to update prices from provider to purchase order lines.

On purchase lines:

#. Add delivery status and invoice status on purchase lines
#. Add button on purchase lines to allow cancelling of remaining qty to be received
#. If not seller is defined or seller price is 0, then sugget accounting cost
#. Add return quantity when you return products with "To Refund" option.

On incoming pickings:

#. Add button "Add Purchase Lines" to add moves from other pickings that are still pending.

On purchase invoices:

#. Add "add picking" functionlity on purchase invoices so picking lines that has some qty to be invoiced, is added to the invoice. This is different to "add PO" that add all lines no matter if they are to be invoiced or not. We keep this functionality because if a supplier send you an invoice of same lines that should be invoiced, you still have de possiblity to add them.
#. Add a button "Update Supplier Prices" to update (or create prices) for this provider and all products loaded on the invoice.

On Products:

#. Allows to search by suppliers and to group by main supplier on product and product variants.

On Stock Moves:

#. Add button to access to purchase order related.



Installation
============

To install this module, you need to:

#. Just install this module.


Configuration
=============

To configure this module, you need to:

#. No configuration nedeed.

Usage
=====

To use this module, you need to:

#. Go to ...

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
