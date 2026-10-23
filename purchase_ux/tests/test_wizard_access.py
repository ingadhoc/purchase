##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged

WIZARDS = ("purchase.change.currency", "purchase.order.line.add_to_invoice")


@tagged("post_install", "-at_install")
class TestWizardAccess(TransactionCase):
    """Access granted by security/ir.access.csv to the module wizards."""

    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.purchase_user = new_test_user(cls.env, login="purchase_ux_buyer", groups="purchase.group_purchase_user")
        cls.internal_user = new_test_user(cls.env, login="purchase_ux_internal", groups="base.group_user")
        cls.order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.env["res.partner"].create({"name": "Wizard Access Vendor"}).id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.env["product.product"].create({"name": "Wizard Access Product"}).id,
                            "product_qty": 2,
                            "price_unit": 100.0,
                        }
                    )
                ],
            }
        )
        cls.other_currency = cls.env["res.currency"].search(
            [("id", "!=", cls.order.currency_id.id), ("active", "in", [True, False])], limit=1
        )
        cls.other_currency.active = True

    def test_purchase_user_can_create_read_write(self):
        for model in WIZARDS:
            wizard_model = self.env[model].with_user(self.purchase_user)
            for operation in ("create", "read", "write"):
                wizard_model.check_access(operation)

    def test_purchase_user_cannot_unlink(self):
        for model in WIZARDS:
            with self.assertRaises(AccessError):
                self.env[model].with_user(self.purchase_user).check_access("unlink")

    def test_internal_user_without_purchase_group_has_no_access(self):
        for model in WIZARDS:
            with self.assertRaises(AccessError):
                self.env[model].with_user(self.internal_user).check_access("create")

    def test_purchase_user_changes_currency(self):
        wizard = (
            self.env["purchase.change.currency"]
            .with_user(self.purchase_user)
            .with_context(active_id=self.order.id)
            .create({"currency_id": self.other_currency.id, "currency_rate": 2.0})
        )
        wizard.change_currency()
        self.assertEqual(self.order.currency_id, self.other_currency)
        self.assertEqual(self.order.order_line.price_unit, 200.0)
