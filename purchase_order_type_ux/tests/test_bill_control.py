from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestOrderTypeBillControl(PurchaseTestCommon):
    """The bill control of the order type bills like Odoo: an exchange does not lower the quantity to bill."""

    # Run as admin: these tests set up warehouses and post vendor bills
    _test_user_groups = ()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Bill Control Vendor"})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.warehouse.reception_steps = "one_step"
        cls.order_type = cls.env["purchase.order.type"].create(
            {"name": "Bill on ordered quantities", "purchase_method": "purchase"}
        )
        # The product bills on received quantities, so only the order type can bill on ordered ones
        cls.storable = cls.env["product.product"].create(
            {"name": "Bill control product", "type": "consu", "is_storable": True, "purchase_method": "receive"}
        )

    def _validate(self, picking):
        picking.action_assign()
        for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.button_validate()

    def _received_po(self, qty=10):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "order_type": self.order_type.id,
                "picking_type_id": self.warehouse.in_type_id.id,
                "order_line": [
                    Command.create({"product_id": self.storable.id, "product_qty": qty, "price_unit": 10.0})
                ],
            }
        )
        po.button_confirm()
        self._validate(po.picking_ids)
        return po

    def _bill(self, po):
        po.action_create_invoice()
        po.invoice_ids.invoice_date = po.date_order
        po.invoice_ids.action_post()

    def _exchange(self, po, qty):
        receipt = po.picking_ids.filtered(lambda p: p.state == "done")
        return_picking = self.env["stock.picking"].browse(receipt.action_return()["res_id"])
        return_picking.move_ids.write({"product_uom_qty": qty, "to_refund": True})
        return_picking.action_confirm()
        self._validate(return_picking)
        exchange = self.env["stock.picking"].browse(return_picking.action_exchange()["res_id"])
        self._validate(exchange)

    def test_exchange_before_bill(self):
        """Ordered 10, 2 exchanged before billing: 10 to bill."""
        po = self._received_po()
        self._exchange(po, 2)
        line = po.order_line
        self.assertEqual(line.qty_received, 10)
        self.assertEqual(line.qty_to_invoice, 10)

    def test_exchange_after_bill(self):
        """Ordered and billed 10, 1 exchanged afterwards: nothing to bill and the order stays billed."""
        po = self._received_po()
        self._bill(po)
        self._exchange(po, 1)
        line = po.order_line
        self.assertEqual(line.qty_to_invoice, 0)
        self.assertEqual(line.invoice_status, "invoiced")
