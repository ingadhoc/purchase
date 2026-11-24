.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

======================
Purchase Order Type UX
======================

On purchase order type:

#. Adds to the purchase order type the operation type for receipts ("Deliver To"), the fiscal position, the invoice
   company, the billing journal and the bill control (ordered or received quantities).
#. When the type is selected on a purchase order, sets the operation type and the fiscal position of the type. Orders
   created with a type that has a fiscal position get it too.
#. Purchase orders of that type bill on the type's bill control.
#. Vendor bills created from those orders use the type's billing journal and invoice company.
#. Adds a per-type "Lock on Confirmation" flag that locks orders of that type when they are approved. It is
   additive to the global "Lock Confirmed Orders" setting, which always prevails.

Installation
============

To install this module, you need to:

#. Just install this module.


Configuration
=============

To configure this module, you need to:

#. No configuration needed.

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
