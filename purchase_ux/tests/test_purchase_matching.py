##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPurchaseMatching(AccountTestInvoicingCommon):
    """Lines offered by the purchase matching action, ordered/received/billed."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # forcing the invoice status of a PO is restricted to settings managers
        cls.env.user.groups_id |= cls.env.ref("base.group_system")
        cls.vendor = cls.env["res.partner"].create({"name": "Test Vendor Matching"})
        # a service controlled on received quantities lets us set qty_received by hand
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Service On Received",
                "type": "service",
                "purchase_method": "receive",
            }
        )

    def _line(self, ordered, received=0.0, forced=False):
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    Command.create({"product_id": self.product.id, "product_qty": ordered, "price_unit": 100.0})
                ],
            }
        )
        purchase.button_confirm()
        purchase.order_line.qty_received = received
        purchase.force_invoiced_status = forced
        return purchase.order_line

    def _bill(self, line, quantity, move_type="in_invoice"):
        self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": self.vendor.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "quantity": quantity,
                            "price_unit": 100.0,
                            "purchase_line_id": line.id,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        ).action_post()

    def _offered(self, move_type="in_invoice"):
        move = self.env["account.move"].create({"move_type": move_type, "partner_id": self.vendor.id})
        action = move.action_purchase_matching()
        self.env.flush_all()  # the matching model is a SQL view read from the database
        return self.env["purchase.bill.line.match"].search(action["domain"]).pol_id

    def test_bill_not_received(self):
        self.assertIn(self._line(100), self._offered())

    def test_bill_partially_received(self):
        self.assertIn(self._line(100, received=60), self._offered())

    def test_bill_over_receipt(self):
        line = self._line(40, received=41)
        self._bill(line, 40)
        self.assertIn(line, self._offered())

    def test_bill_fully_billed(self):
        line = self._line(100, received=100)
        self._bill(line, 100)
        self.assertNotIn(line, self._offered())

    def test_bill_forced_invoiced_status(self):
        self.assertNotIn(self._line(100, forced="invoiced"), self._offered())

    def test_bill_set_invoiced_button(self):
        """The Set Invoiced button closes the order for billing, and it sticks."""
        line = self._line(100, received=60)
        line.order_id.button_set_invoiced()
        self.assertEqual(line.order_id.force_invoiced_status, "invoiced")
        self.assertEqual(line.order_id.invoice_status, "invoiced")
        self.assertNotIn(line, self._offered())
        line.qty_received = 80  # a later recompute must not bring it back
        self.assertEqual(line.order_id.invoice_status, "invoiced")
        self.assertNotIn(line, self._offered())

    def test_refund_pending_from_return(self):
        line = self._line(600, received=500)
        self._bill(line, 600)
        self.assertIn(line, self._offered(move_type="in_refund"))

    def test_refund_already_credited(self):
        line = self._line(600, received=500)
        self._bill(line, 600)
        self._bill(line, 100, move_type="in_refund")
        self.assertNotIn(line, self._offered(move_type="in_refund"))
