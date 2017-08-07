.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===============================
Purchase Usability Improvements
===============================

Several Improvements to purchases

#. Make that, by default, links to purchase orders you "purchase" data and not only "quoatation"

On purchase orders:
#. Add button "Re-Open" on purchase orders to came back from "Done" to "Purchase Order" state, only available to purchase manager
#. Make button send by email also available on done state on purchase orders
#. Odoo consider that a purchase order on done state has nothing to be invoiced, we change that behaviour to keep it as on sale orders
#. Make purchase quotations menu only visible with technical features
#. Make purchase orders menu show all purchase records (quotations, and confirmed ones)
#. Add delivery status on purchases
#. Add print PO on purchase and done status
#. Add button to force "invoiced" only for admin with tec features

On purchase lines:
#. Add delivery status and invoice status on purchase lines
#. Backport of a fix of odoo v10 to deduct refunds on qty_invoiced field (on v9, by default, they are summed)
#. Add button on purchase lines to allow cancelling of remaining qty to be received

On incoming pickings:
#. Add new parameter "Merge Incoming Picking" on incoming picking types, if set true, when confirming a purchase order, if an open picking exists for same partner and picking type, incoming moves will be merged into that picking (TODO remove this functionality)
#. Add button "Add Purchase Lines" to add moves from other pickings that are still pending.
 
On stock moves:
#. Button with link to related purchase order

On purchase invoices:
#. Add "add picking" functionlity on purchase invoices so picking lines that has some qty to be invoiced, is added to the invoice. This is different to "add PO" that add all lines no matter if they are to be invoiced or not. We keep this functionality because if a supplier send you an invoice of same lines that shouldt be invoiced, you still have de possiblity to add them


TODO: tal vez querramos implementar que el check de procurements sea analogo al de moves para que se marque realizado si moves en done o cancel, buscar en purchase "return all(move.state == 'done' for move in procurement.move_ids)"

Installation
============

To install this module, you need to:

#. Just install this module.


Configuration
=============

To configure this module, you need to:

#. No configuration nedeed.


.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.adhoc.com.ar/

.. repo_id is available in https://github.com/OCA/maintainer-tools/blob/master/tools/repos_with_ids.txt
.. branch is "8.0" for example

Known issues / Roadmap
======================

Notes abount "Add Purchase Lines":
Teniamos dos opciones:
1) al confirmar PO dejamos que se genere picking y permitimos robar moves desde otros pickings. tener en cuenta 
    a) si picking queda limpio ver de cancelar o borrar
    b) si resto cantidad cuando esto haciendo add purchase lines, a que picking se los asigno)
2) que se generen moves sin pickings, tener en cuenta:
    a) necesitamos confirmar los moves con action_confirm (pero evitar que se genere picking) o manualmente
    b) tenemos que gestionar que cancelar po cancele los moves
    c) cambiar metodo de agregar lineas para que busque moves sin picking
    d) que al procesar cantidad menor haya otra opción o el "back order" no cree picking (si no, no los vamos a poder robar)
    e) no es back compatible, lo que ya esta creado no se puede chupar

la opcion 1 parece mas simple pero el problema es que si disminuimos cantidad agregada a un picking, cuando la sacamos, a que picking se la asignamos? Igualmente fuimos por la 1 para tratar de ser menos invacivos


Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/stock/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* ADHOC SA: `Icon <http://fotos.subefotos.com/83fed853c1e15a8023b86b2b22d6145bo.png>`_.

Contributors
------------


Maintainer
----------

.. image:: http://fotos.subefotos.com/83fed853c1e15a8023b86b2b22d6145bo.png
   :alt: Odoo Community Association
   :target: https://www.adhoc.com.ar

This module is maintained by the ADHOC SA.

To contribute to this module, please visit https://www.adhoc.com.ar.
