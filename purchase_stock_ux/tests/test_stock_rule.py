from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockRule(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Vendor"})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.product = cls.env["product.product"].create(
            {
                "name": "Product without vendor price",
                "is_storable": True,
                "standard_price": 100.0,
                "route_ids": [Command.link(cls.env.ref("purchase_stock.route_warehouse0_buy").id)],
                "seller_ids": [Command.create({"partner_id": cls.partner.id, "price": 0.0})],
            }
        )

    def _run_buy_procurement(self, qty):
        self.env["stock.rule"].run(
            [
                self.env["stock.rule"].Procurement(
                    self.product,
                    qty,
                    self.product.uom_id,
                    self.warehouse.lot_stock_id,
                    "Test",
                    "Test",
                    self.env.company,
                    {"warehouse_id": self.warehouse},
                )
            ]
        )

    def test_merge_po_line_falls_back_to_standard_price(self):
        """Merging a procurement into an existing PO line uses the product cost when the vendor has no price."""
        self._run_buy_procurement(1)
        self._run_buy_procurement(1)
        line = self.env["purchase.order.line"].search([("product_id", "=", self.product.id)])
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_qty, 2)
        self.assertEqual(line.price_unit, 100.0)
