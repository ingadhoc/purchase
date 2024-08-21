from odoo.tests import tagged, Form, TransactionCase
from odoo.exceptions import UserError
from odoo.addons.product.tests import common

@tagged('-at_install', 'post_install')
class TestPurchaseOrder(common.TestProductCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPurchaseOrder, cls).setUpClass()
        cls.purchase_order_model = cls.env['purchase.order']
        cls.purchase_order_line_model = cls.env['purchase.order.line']
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })

    def setUp(self):
        super(TestPurchaseOrder, self).setUp()
        self.purchase_order = self.purchase_order_model.create({
            'partner_id': self.partner.id,
        })
        self.purchase_order_line = self.purchase_order_line_model.create({
            'order_id': self.purchase_order.id,
            'product_id': self.product.id,
            'product_qty': 10,
            'price_unit': 100,
        })

    def test_internal_notes_in_invoice(self):
        """Test that internal notes are correctly transferred to the invoice."""
        po = self.purchase_order_model.create({
            'partner_id': self.partner.id,
            'internal_notes': '<p>Test Internal Notes</p>',
        })
        po_line = self.purchase_order_line_model.create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_qty': 1,
            'price_unit': 100,
        })

        invoice_vals = po._prepare_invoice()
        self.assertEqual(invoice_vals.get('internal_notes'), po.internal_notes, "Internal notes not transferred to invoice correctly.")

    def test_update_prices_with_supplier_cost(self):
        """Test that supplier prices are updated correctly."""
        po_line = self.purchase_order_line_model.create({
            'order_id': self.purchase_order.id,
            'product_id': self.product.id,
            'product_qty': 10,
            'price_unit': 15,
        })
        self.purchase_order.update_prices_with_supplier_cost()
        supplier_info = self.env['product.supplierinfo'].search([('product_tmpl_id', '=', self.product.product_tmpl_id.id)])
        self.assertTrue(supplier_info, "Supplier info not created.")
        self.assertEqual(supplier_info.price, 15, "Supplier price not updated correctly.")

    def test_button_set_invoiced(self):
        """Test the manual setting of an order as invoiced."""
        po = self.purchase_order_model.create({
            'partner_id': self.partner.id,
            'state': 'purchase',
        })
        po.button_set_invoiced()
        self.assertEqual(po.invoice_status, 'invoiced', "Invoice status not set correctly.")


