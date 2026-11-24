from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestCreateFiscalPosition(PurchaseTestCommon):
    """Orders created by code get the fiscal position of their own order type."""

    _test_user_groups = ()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        FiscalPosition = cls.env["account.fiscal.position"]
        cls.fp_a = FiscalPosition.create({"name": "FP type A"})
        cls.fp_b = FiscalPosition.create({"name": "FP type B"})
        cls.fp_vals = FiscalPosition.create({"name": "FP from vals"})
        OrderType = cls.env["purchase.order.type"]
        cls.type_a = OrderType.create({"name": "Type A", "fiscal_position_id": cls.fp_a.id})
        cls.type_b = OrderType.create({"name": "Type B", "fiscal_position_id": cls.fp_b.id})
        cls.type_no_fp = OrderType.create({"name": "Type without fiscal position"})

    def _vals(self, order_type, **extra):
        return {
            "partner_id": self.vendor.id,
            "order_type": order_type.id,
            "order_line": [Command.create({"product_id": self.product.id, "product_qty": 1, "price_unit": 10.0})],
            **extra,
        }

    def test_batch_with_different_types(self):
        """Each order of a batch gets the fiscal position of its own type."""
        orders = self.env["purchase.order"].create(
            [self._vals(self.type_a), self._vals(self.type_b), self._vals(self.type_no_fp)]
        )
        self.assertEqual(orders[0].fiscal_position_id, self.fp_a)
        self.assertEqual(orders[1].fiscal_position_id, self.fp_b)
        self.assertNotIn(orders[2].fiscal_position_id, self.fp_a | self.fp_b)

    def test_fiscal_position_in_vals_is_kept(self):
        """A fiscal position given in the values is not replaced by the type's."""
        order = self.env["purchase.order"].create(self._vals(self.type_a, fiscal_position_id=self.fp_vals.id))
        self.assertEqual(order.fiscal_position_id, self.fp_vals)
