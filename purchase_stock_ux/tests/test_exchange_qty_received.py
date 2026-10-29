from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestExchangeQtyReceived(PurchaseTestCommon):
    """An exchange on a vendor return kept from 19 without "to refund" must not change the received quantity."""

    # Run as admin, as in 19: these tests set up warehouses
    _test_user_groups = ()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Exchange Vendor"})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.warehouse.reception_steps = "one_step"

    def _product(self, purchase_method):
        return self.env["product.product"].create(
            {
                "name": f"Exchange product {purchase_method}",
                "type": "consu",
                "is_storable": True,
                "purchase_method": purchase_method,
            }
        )

    def _validate(self, picking):
        picking.action_assign()
        for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.button_validate()

    def _received_and_invoiced_po(self, product, qty=10):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.warehouse.in_type_id.id,
                "order_line": [Command.create({"product_id": product.id, "product_qty": qty, "price_unit": 10.0})],
            }
        )
        po.button_confirm()
        self._validate(po.picking_ids)
        po.action_create_invoice()
        po.invoice_ids.invoice_date = po.date_order
        po.invoice_ids.action_post()
        return po

    def _exchange(self, po, qty, to_refund):
        receipt = po.picking_ids.filtered(lambda p: p.state == "done")
        return_picking = self.env["stock.picking"].browse(receipt.action_return()["res_id"])
        return_picking.move_ids.write({"product_uom_qty": qty, "to_refund": to_refund})
        return_picking.action_confirm()
        self._validate(return_picking)
        exchange = self.env["stock.picking"].browse(return_picking.action_exchange()["res_id"])
        self._validate(exchange)
        self.assertEqual(len(po.picking_ids.filtered(lambda p: p.state == "done")), 3)

    def test_exchange_of_return_without_refund(self):
        """Return made in 19 with "to refund" unchecked, exchanged in 20: 10 received and nothing to bill."""
        for purchase_method in ("receive", "purchase"):
            with self.subTest(purchase_method=purchase_method):
                po = self._received_and_invoiced_po(self._product(purchase_method))
                self._exchange(po, 1, to_refund=False)
                line = po.order_line
                self.assertEqual(line.qty_received, 10)
                self.assertEqual(line.qty_returned, 0)
                self.assertEqual(line.qty_to_invoice, 0)

    def test_exchange_with_refund(self):
        """Exchange of a 20 return: the return lowers the received quantity and the replacement raises it."""
        po = self._received_and_invoiced_po(self._product("receive"))
        self._exchange(po, 1, to_refund=True)
        self.assertEqual(po.order_line.qty_received, 10)
        self.assertEqual(po.order_line.qty_to_invoice, 0)
