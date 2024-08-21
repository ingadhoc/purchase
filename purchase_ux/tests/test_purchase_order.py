from odoo.addons.product.tests import common


class TestPurchaseOrder(common.TestProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'standard_price': 50.0,
            'list_price': 100.0,
        })

        cls.supplier_info = cls.env['product.supplierinfo'].create({
            'partner_id': cls.partner.id,
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'price': 80.0,
            'currency_id': cls.env.company.currency_id.id,
            'company_id': cls.env.company.id,
        })

        cls.purchase_order = cls.env['purchase.order'].create({
            'partner_id': cls.partner.id,
            'internal_notes': '<p>Test internal notes</p>',
        })
        cls.purchase_order_line = cls.env['purchase.order.line'].create({
            'order_id': cls.purchase_order.id,
            'product_id': cls.product.id,
            'price_unit': 100.0,
        })

    def test_update_prices(self):
        """Test that the purchase order prices are updated correctly from supplier prices."""

        self.purchase_order.update_prices()
        for line in self.purchase_order.order_line:
            self.assertEqual(line.price_unit, self.supplier_info.price, "The price should be updated.")

    def test_update_supplier_price(self):
        """Test if supplier price is updated after purchase order."""
        self.purchase_order.update_prices_with_supplier_cost()

        supplier_info = self.env['product.supplierinfo'].search([
            ('partner_id', '=', self.partner.id),
            ('product_tmpl_id', '=', self.product.product_tmpl_id.id),
        ])
        self.assertTrue(supplier_info, "Supplier info should exit")
        self.assertEqual(supplier_info.price, 100.0, "Supplier price should be updated to 100.0")

    def test_internal_notes_in_invoice(self):
        """
        Test that internal notes are correctly transferred to the invoice.
        """
        invoice_vals = self.purchase_order._prepare_invoice()
        self.assertEqual(invoice_vals.get('internal_notes'), '<p>Test internal notes</p>', "Internal notes should be transferred to the invoice.")
