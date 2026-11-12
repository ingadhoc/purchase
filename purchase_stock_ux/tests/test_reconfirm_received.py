from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon
from odoo.exceptions import ValidationError


class TestReconfirmReceived(PurchaseTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Reconfirm Vendor"})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.warehouse.reception_steps = "one_step"
        cls.warehouse.in_type_id.block_picking_deletion = True
        cls.storable = cls.env["product.product"].create(
            {"name": "Reconfirm product", "type": "consu", "is_storable": True}
        )

    def test_reconfirm_fully_received_order(self):
        """A fully received order can be cancelled, reset and confirmed again with blocked picking deletion."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.warehouse.in_type_id.id,
                "order_line": [Command.create({"product_id": self.storable.id, "product_qty": 2, "price_unit": 10.0})],
            }
        )
        po.button_confirm()
        receipt = po.picking_ids
        receipt.action_assign()
        receipt.move_ids.quantity = 2
        receipt.move_ids.picked = True
        receipt.button_validate()
        self.assertEqual(receipt.state, "done")

        po.button_cancel()
        po.button_draft()
        po.button_confirm()

        self.assertEqual(po.state, "purchase")
        self.assertEqual(po.picking_ids, receipt)
        self.assertEqual(po.order_line.qty_received, 2)

    def test_empty_draft_receipt_deletion_still_blocked(self):
        """Outside order confirmation, an empty draft receipt still can't be deleted."""
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": self.warehouse.in_type_id.default_location_src_id.id,
                "location_dest_id": self.warehouse.in_type_id.default_location_dest_id.id,
            }
        )
        with self.assertRaises(ValidationError):
            picking.unlink()
