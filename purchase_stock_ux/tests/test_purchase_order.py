from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon
from odoo.tools.float_utils import float_is_zero


class TestPurchaseOrder(PurchaseTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
            }
        )

        cls.purchase_order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_qty": 10,
                            "price_unit": 100,
                        }
                    ),
                ],
                "internal_notes": "Test internal notes",
            }
        )

        cls.purchase_order.button_confirm()

<<<<<<< bed80522437e95ca8fdfb04e2f801b9beced261b
    def _create_return_for_product(self, picking, product, qty, to_refund=True):
        """Return `qty` units of `product` from a validated picking."""
        return_wiz = (
            self.env["stock.return.picking"].with_context(active_id=picking.id, active_model="stock.picking").create({})
        )
        for line in return_wiz.product_return_moves:
            if line.product_id == product:
                line.quantity = qty
                line.to_refund = to_refund
            else:
                line.quantity = 0
        return_picking = return_wiz._create_return()
        return_picking.move_ids.quantity = qty
        return_picking.with_context(skip_backorder=True).button_validate()
        return return_picking

    def test_invoice_excludes_fully_returned_lines(self):
        """Mixed PO: invoiceable line + fully-returned line → only invoiceable line in invoice."""
        product2 = self.env["product.product"].create(
            {
                "name": "Product 2 Storable",
                "is_storable": True,
                "purchase_method": "purchase",
            }
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 10,
                            "price_unit": 50,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": product2.id,
                            "product_qty": 5,
                            "price_unit": 20,
                        }
                    ),
                ],
            }
        )
        po.button_confirm()

        picking = po.picking_ids
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.with_context(skip_backorder=True).button_validate()

        # Fully return only product2 (line 2)
        self._create_return_for_product(picking, product2, qty=5)

        line2 = po.order_line.filtered(lambda l: l.product_id == product2)
        self.assertTrue(
            float_is_zero(line2.qty_to_invoice, precision_digits=2),
            "Fully returned line must have qty_to_invoice = 0",
        )

        invoice = self.env["account.move"].browse(po.action_create_invoice()["res_id"])
        product_lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == "product")
        self.assertEqual(len(product_lines), 1, "Invoice must not include the fully-returned line")
        self.assertEqual(product_lines.product_id, self.product)

    def test_invoice_partial_return_no_regression(self):
        """Partial return → invoice for the remaining net quantity, no zero lines."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 10,
                            "price_unit": 50,
                        }
                    ),
                ],
            }
        )
        po.button_confirm()

        picking = po.picking_ids
        picking.move_ids.quantity = 10
        picking.with_context(skip_backorder=True).button_validate()

        self._create_return_for_product(picking, self.product, qty=4)

        line = po.order_line
        self.assertAlmostEqual(line.qty_to_invoice, 6.0, places=2)

        invoice = self.env["account.move"].browse(po.action_create_invoice()["res_id"])
        product_lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == "product")
        self.assertEqual(len(product_lines), 1)
        self.assertAlmostEqual(product_lines.quantity, 6.0, places=2)

    def test_real_return_sets_qty_returned(self):
        """A genuine refundable return to the vendor must feed qty_returned."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 10,
                            "price_unit": 50,
                        }
                    ),
                ],
            }
        )
        po.button_confirm()

        picking = po.picking_ids
        picking.move_ids.quantity = 10
        picking.with_context(skip_backorder=True).button_validate()

        self._create_return_for_product(picking, self.product, qty=4)

        self.assertAlmostEqual(po.order_line.qty_returned, 4.0, places=2)

    def test_subcontract_receipt_not_flagged_as_returned(self):
        """Ticket 121292: a ``to_refund`` move that is NOT a purchase return
        (e.g. the subcontracting receipt when the MO is closed before validating
        the receipt) must not inflate qty_returned, otherwise the line drops to
        qty_to_invoice = 0 and the received goods cannot be billed."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 10,
                            "price_unit": 50,
                        }
                    ),
                ],
            }
        )
        po.button_confirm()

        picking = po.picking_ids
        picking.move_ids.quantity = 10
        picking.with_context(skip_backorder=True).button_validate()
        line = po.order_line

        # Mimic the subcontracting receipt move: done, to_refund, internal source
        # and destination (no return to supplier, no origin_returned_move_id), so
        # ``_is_purchase_return()`` is False even though ``to_refund`` is True.
        internal_loc = picking.location_dest_id
        bogus_move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 10,
                "product_uom": self.product.uom_id.id,
                "location_id": internal_loc.id,
                "location_dest_id": internal_loc.id,
                "to_refund": True,
                "purchase_line_id": line.id,
            }
        )
        bogus_move.write({"state": "done"})

        self.assertFalse(
            bogus_move._is_purchase_return(),
            "Sanity check: the crafted move must not be a purchase return",
        )
        line.invalidate_recordset(["qty_returned", "qty_to_invoice"])
        self.assertAlmostEqual(line.qty_returned, 0.0, places=2, msg="Subcontract receipt must not count as returned")
        self.assertAlmostEqual(line.qty_to_invoice, 10.0, places=2, msg="Received goods must stay invoiceable")

    def test_invoice_keeps_note_lines(self):
        """Note lines also have qty_to_invoice = 0 but must stay on the bill."""
        product2 = self.env["product.product"].create(
            {
                "name": "Product 2 Storable",
                "is_storable": True,
                "purchase_method": "purchase",
            }
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 10,
                            "price_unit": 50,
                        }
                    ),
                    Command.create(
                        {
                            "display_type": "line_note",
                            "name": "Handle with care",
                            "product_id": False,
                            "product_qty": 0.0,
                            "product_uom_id": False,
                            "price_unit": 0.0,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": product2.id,
                            "product_qty": 5,
                            "price_unit": 20,
                        }
                    ),
                ],
            }
        )
        po.button_confirm()

        picking = po.picking_ids
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.with_context(skip_backorder=True).button_validate()

        # Fully return product2 so its line drops to qty_to_invoice = 0
        self._create_return_for_product(picking, product2, qty=5)

        invoice = self.env["account.move"].browse(po.action_create_invoice()["res_id"])
        product_lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == "product")
        note_lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == "line_note")
        self.assertEqual(len(product_lines), 1, "Only the invoiceable product line must remain")
        self.assertEqual(product_lines.product_id, self.product)
        self.assertEqual(note_lines.name, "Handle with care", "Note lines must be kept on the bill")

||||||| 44a1146a97c5cbcb5e7733eb02d6d7bf66bad909
=======
    def test_forced_invoiced_status_on_lines(self):
        """La OC forzada a facturada mantiene ese estado en sus líneas."""
        self.env.user.groups_id |= self.env.ref("base.group_system")
        self.purchase_order.force_invoiced_status = "invoiced"
        self.assertEqual(self.purchase_order.order_line.invoice_status, "invoiced")

>>>>>>> ded69f3dfd06ef63fd68a2fc2a022ae7bf5ffb24
    def test_unlink_line_with_done_dest_move(self):
        """Borrar una línea de OC cuya entrega destino ya está 'done' no debe fallar.

        Reproduce el caso MTO en el que la venta se entregó desde stock disponible
        (movimiento destino en 'done') y luego se quiere eliminar la línea de la OC
        que la abastecía. El unlink estándar de purchase_stock intentaría cancelar
        ese movimiento ya hecho y lanzaría UserError; con el fix se desvincula en
        lugar de cancelarlo.
        """
        draft_po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 5,
                            "price_unit": 50,
                        }
                    ),
                ],
            }
        )
        pol = draft_po.order_line
        pol.propagate_cancel = True

        done_move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 5,
                "product_uom": self.product.uom_id.id,
                "location_id": self.env.ref("stock.stock_location_stock").id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            }
        )
        done_move.write({"state": "done"})
        pol.move_dest_ids = [Command.link(done_move.id)]

        # No debe lanzar UserError por el movimiento 'Hecho'.
        pol.unlink()

        # El movimiento entregado debe quedar intacto.
        self.assertEqual(done_move.state, "done")
        self.assertFalse(draft_po.order_line)

    def _confirmed_po_with_note(self):
        """OC confirmada con una línea de producto y una nota."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 10,
                            "price_unit": 50,
                        }
                    ),
                    Command.create(
                        {
                            "display_type": "line_note",
                            "name": "Handle with care",
                            "product_id": False,
                            "product_qty": 0.0,
                            "product_uom_id": False,
                            "price_unit": 0.0,
                        }
                    ),
                ],
            }
        )
        po.button_confirm()
        return po

    def test_receipt_status_note_line_has_no_status(self):
        """Las notas no tienen nada por recibir: receipt_status vacío, no 'pending'."""
        po = self._confirmed_po_with_note()
        note = po.order_line.filtered(lambda line: line.display_type)

        self.assertFalse(note.receipt_status, "Una nota no debe quedar como pendiente de recibir")

    def test_receipt_status_zero_qty_line_is_not_pending(self):
        """Línea anulada bajando la cantidad a 0: no queda nada por recibir."""
        po = self._confirmed_po_with_note()
        line = po.order_line.filtered(lambda line: not line.display_type)
        self.assertEqual(line.receipt_status, "pending", "Sanity check: sin recibir arranca pendiente")

        line.product_qty = 0

        self.assertEqual(line.receipt_status, "full", "Sin cantidad pedida no queda nada por recibir")

    def test_receipt_status_partial_and_full(self):
        """Recepción parcial y total siguen mapeando a 'partial' y 'full'."""
        po = self._confirmed_po_with_note()
        line = po.order_line.filtered(lambda line: not line.display_type)

        picking = po.picking_ids
        picking.move_ids.quantity = 4
        picking.with_context(skip_backorder=True).button_validate()
        self.assertEqual(line.receipt_status, "partial")

        backorder = po.picking_ids - picking
        backorder.move_ids.quantity = 6
        backorder.with_context(skip_backorder=True).button_validate()
        self.assertEqual(line.receipt_status, "full")
