.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

======================================================
Purchase Usability interatction with Refund management
======================================================

Este módulo es un mix entre cosas de "purchase_stock_picking_return_invoicing" y de odoo v11. No usamos "purchase_stock_picking_return_invoicing" ya que tenía muchas cosas que ya implementamos en stock_usability.

TODO: falta resolver bien el tema de las notas de crédito, por ahora hace facturas en negativo

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
