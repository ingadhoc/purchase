from odoo.addons.product.tests import common


class TestPurchaseOrder(common.TestProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
            }
        )

        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "standard_price": 50.0,
                "list_price": 100.0,
            }
        )

        cls.supplier_info = cls.env["product.supplierinfo"].create(
            {
                "partner_id": cls.partner.id,
                "product_tmpl_id": cls.product.product_tmpl_id.id,
                "price": 80.0,
                "currency_id": cls.env.company.currency_id.id,
                "company_id": cls.env.company.id,
            }
        )

        cls.purchase_order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "internal_notes": "<p>Test internal notes</p>",
            }
        )
        cls.purchase_order_line = cls.env["purchase.order.line"].create(
            {
                "order_id": cls.purchase_order.id,
                "product_id": cls.product.id,
                "price_unit": 100.0,
            }
        )

    def test_update_prices(self):
        """Test that the purchase order prices are updated correctly from supplier prices."""

        self.purchase_order.update_prices()
        for line in self.purchase_order.order_line:
            self.assertEqual(line.price_unit, self.supplier_info.price, "The price should be updated.")

    def test_update_supplier_price(self):
        """Test if supplier price is updated after purchase order."""
        self.purchase_order.update_prices_with_supplier_cost()

        supplier_info = self.env["product.supplierinfo"].search(
            [
                ("partner_id", "=", self.partner.id),
                ("product_tmpl_id", "=", self.product.product_tmpl_id.id),
            ]
        )
        self.assertTrue(supplier_info, "Supplier info should exit")
        self.assertEqual(supplier_info.price, 100.0, "Supplier price should be updated to 100.0")

    def test_update_company_less_supplier_price(self):
        """A shared (company-less) supplier line must be updated in place, not
        shadowed by a new company-scoped line (ticket 129603).

        When buying from a secondary company, scoping the created/searched
        supplierinfo to the order company left the company-less cost (the one
        the planned price reads through the main company) untouched.
        """
        shared_info = self.env["product.supplierinfo"].create(
            {
                "partner_id": self.partner.id,
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "price": 80.0,
                "currency_id": self.env.company.currency_id.id,
                "company_id": False,
            }
        )

        self.purchase_order.update_prices_with_supplier_cost()

        self.assertFalse(shared_info.company_id, "The shared line must stay company-less.")
        self.assertEqual(shared_info.price, 100.0, "The shared line must be the one updated.")
        self.assertEqual(self.supplier_info.price, 80.0, "The company-scoped line must not be touched.")
        all_lines = self.env["product.supplierinfo"].search(
            [
                ("partner_id", "=", self.partner.id),
                ("product_tmpl_id", "=", self.product.product_tmpl_id.id),
            ]
        )
        self.assertEqual(all_lines, shared_info | self.supplier_info, "No new supplier line should be created.")

    def test_internal_notes_in_invoice(self):
        """
        Test that internal notes are correctly transferred to the invoice.
        """
        invoice_vals = self.purchase_order._prepare_invoice()
        self.assertEqual(
            invoice_vals.get("internal_notes"),
            "<p>Test internal notes</p>",
            "Internal notes should be transferred to the invoice.",
        )
