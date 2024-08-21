from odoo.tests import tagged, TransactionCase
from odoo.tools import float_compare
from odoo import fields

@tagged('-at_install', 'post_install')
class TestPurchaseOrderLine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.purchase_order_model = cls.env['purchase.order']
        cls.purchase_order_line_model = cls.env['purchase.order.line']
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'detailed_type': 'consu',
            'standard_price': 10.0,
            'purchase_method': 'purchase',
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })

    def test_invoice_status_computation(self):
        """Test that invoice status is computed correctly based on the order state and line quantities."""
        po = self.purchase_order_model.create({
            'partner_id': self.partner.id,
            'state': 'purchase',
        })
        po_line = self.purchase_order_line_model.create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_qty': 10,
            'qty_invoiced': 0,
            'price_unit': 15,
            'date_planned': fields.Date.today(),
        })

        po_line._compute_qty_to_invoice()
        po_line._compute_invoice_status()

        self.assertEqual(po_line.invoice_status, 'to invoice', "Invoice status not computed correctly.")

    # def test_qty_to_invoice_computation(self):
    #     """Test the computation of qty_to_invoice based on received and invoiced quantities."""
    #     po = self.purchase_order_model.create({
    #         'partner_id': self.partner.id,
    #         'state': 'purchase',
    #     })
    #     po_line = self.purchase_order_line_model.create({
    #         'order_id': po.id,
    #         'product_id': self.product.id,
    #         'product_qty': 10,
    #         'qty_invoiced': 5,
    #         'qty_received': 10,
    #         'price_unit': 15,
    #         'date_planned': fields.Date.today(),
    #     })

    #     po_line._compute_qty_to_invoice()
    #     self.assertEqual(float_compare(po_line.qty_to_invoice, 5.0, precision_digits=2), 0, "Qty to invoice not computed correctly.")

    def test_action_line_form(self):
        """Test that the action_line_form returns the correct action."""
        po = self.purchase_order_model.create({
            'partner_id': self.partner.id,
        })
        po_line = self.purchase_order_line_model.create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_qty': 10,
            'price_unit': 15,
            'date_planned': fields.Date.today(),
        })

        action = po_line.action_line_form()
        self.assertEqual(action['res_model'], 'purchase.order.line', "Incorrect action returned for action_line_form.")
        self.assertEqual(action['res_id'], po_line.id, "Incorrect line ID returned in action.")

