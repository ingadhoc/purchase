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
