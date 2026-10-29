.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=================
Purchase Stock UX
=================

Several Improvements to purchases.

On purchase orders:

#. Add a to filter by PO with billable returns.
#. Add receipt status filters and column, and allow to force the receipt status (administrators only).
#. Cancel the remaining quantities of several purchase orders at once from the action menu.
#. Bills do not include lines with nothing to bill after a return.

On purchase lines:

#. Add receipt status on purchase lines
#. Add button on purchase lines to allow cancelling of remaining qty to be received
#. Add returned quantity when products are returned to the vendor.
#. Warn when the ordered quantity of a confirmed line is decreased, suggesting to cancel the remaining quantity.

On incoming pickings:

#. Add moving internal notes of the PO to the picking.

On Stock Moves:

#. Add button to access to purchase order related.

On replenishment:

#. When the vendor has no price, the purchase line takes the product cost.
#. Requests for quotation created by replenishment are grouped by buyer.

On purchase settings:

#. Add option to enable supplier currency selection when creating a PO.
#. Add option to propagate the unit of measure of the purchase order to the picking.


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
