from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestPurchaseRequestAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.requester = new_test_user(
            cls.env, login="pr_requester", groups="purchase_request.group_purchase_request_user"
        )
        cls.extended = new_test_user(
            cls.env, login="pr_extended", groups="purchase_request_ux.group_purchase_request_user_extended"
        )
        cls.plain = new_test_user(cls.env, login="pr_plain", groups="purchase_request.group_purchase_request_user")
        cls.manager = new_test_user(
            cls.env, login="pr_manager", groups="purchase_request.group_purchase_request_manager"
        )
        cls.product = cls.env["product.product"].create({"name": "Requested product", "type": "consu"})
        cls.request = (
            cls.env["purchase.request"]
            .with_user(cls.requester)
            .create(
                {
                    "requested_by": cls.requester.id,
                    "line_ids": [(0, 0, {"product_id": cls.product.id, "product_qty": 2.0})],
                }
            )
        )

    @mute_logger("odoo.addons.base.models.ir_access", "odoo.models")
    def test_extended_user_access(self):
        """The extended group sits between user and manager.

        Given a request owned by another user, a user with the extended group
        reads and writes it (and its chatter), but creates and deletes only
        their own requests and lines. A plain request user does not see it.
        """
        request = self.request.with_user(self.extended)
        Request = self.env["purchase.request"].with_user(self.extended)
        Line = self.env["purchase.request.line"].with_user(self.extended)

        with self.subTest("the extended user reads another user's request and its lines"):
            self.assertEqual(Request.search([("id", "=", self.request.id)]), request)
            self.assertEqual(request.line_ids.mapped("product_qty"), [2.0])

        with self.subTest("writes on another user's request and comments on its chatter"):
            request.description = "Checked by the extended user"
            request.message_post(body="Extended note", subtype_xmlid="mail.mt_note")
            self.assertEqual(self.request.description, "Checked by the extended user")
            self.assertIn("Extended note", self.request.message_ids[0].body)

        with self.subTest("does not create requests or lines on behalf of another user"):
            with self.assertRaises(AccessError), self.cr.savepoint():
                Request.create({"requested_by": self.requester.id})
            with self.assertRaises(AccessError), self.cr.savepoint():
                Line.create({"request_id": self.request.id, "product_id": self.product.id, "product_qty": 1.0})

        with self.subTest("creates and deletes their own request, not another user's"):
            own = Request.create({"requested_by": self.extended.id})
            own.unlink()
            self.assertFalse(own.exists())
            with self.assertRaises(AccessError), self.cr.savepoint():
                request.unlink()
            self.assertTrue(self.request.exists())

        with self.subTest("a request user without the extended group does not see it"):
            plain_request = self.request.with_user(self.plain)
            self.assertFalse(plain_request.search([("id", "=", self.request.id)]))
            with self.assertRaises(AccessError):
                plain_request.read(["name"])

        with self.subTest("the manager has the extended group"):
            self.assertTrue(self.manager.has_group("purchase_request_ux.group_purchase_request_user_extended"))
