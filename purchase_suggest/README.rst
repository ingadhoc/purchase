.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=========================
Purchase Suggest Extended
=========================
This module is an ALTERNATIVE to the module *procurement_suggest* ; it is similar but it only handles the purchase orders and doesn't generate any procurement : the suggestions create a new purchase order directly.

The advantage is that you are not impacted by the faulty procurements (for example :  a procurement generates a PO ; the PO is confirmed ; the related picking is cancelled and deleted -> the procurements will always stay in running without related stock moves !)

To use this module, you need to apply the patch *odoo-purchase_suggest.patch* on the source code of Odoo.

You may want to increase the osv_memory_age_limit (default value = 1h) in Odoo server config file, in order to let some time to the purchase user to finish his work on the purchase suggestions.

We have made de following changes:

#. Add to purchase suggest:
    #. Replenishment cost
    #. Replenishment cost x quantity
    #. Rotation and Location Rotation
    #. pivot and graph view
    #. Add option to add products that dont have an order point (min and max are set to 0.0)

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
