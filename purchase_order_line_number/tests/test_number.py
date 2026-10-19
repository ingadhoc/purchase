##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPurchaseOrderLineNumber(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Vendor"})
        cls.product = cls.env["product.product"].create({"name": "Test Product"})

    def _create_line(self, order, sequence):
        return self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "sequence": sequence,
            }
        )

    def test_number_follows_sequence(self):
        """The number is the position of the line sorted by sequence, not creation order"""
        order = self.env["purchase.order"].create({"partner_id": self.partner.id})
        line_c = self._create_line(order, 30)
        line_a = self._create_line(order, 10)
        line_b = self._create_line(order, 20)
        self.assertEqual(line_a.number, 1)
        self.assertEqual(line_b.number, 2)
        self.assertEqual(line_c.number, 3)
