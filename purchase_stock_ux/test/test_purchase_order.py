# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import SingleTransactionCase
from odoo.tests import Form, tagged
from odoo.exceptions import AccessError


@tagged('post_install', '-at_install')
class TestPurchaseOrder(SingleTransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a users
        group_purchase_user = cls.env.ref('purchase.group_purchase_user')
        group_employee = cls.env.ref('base.group_user')
        group_system = cls.env.ref('base.group_system')

        cls.purchase_user = cls.env['res.users'].with_context(
            no_reset_password=True
        ).create({
            'name': 'Purchase user',
            'login': 'purchaseUser',
            'email': 'pu@odoo.com',
            'groups_id': [(6, 0, [group_purchase_user.id, group_employee.id])],
        })

        cls.vendor = cls.env['res.partner'].create({
            'name': 'Supplier',
            'email': 'supplier.serv@supercompany.com',
        })
        cls.product = cls.env['product.product'].create({
            'name': "Product",
            'standard_price': 200.0,
            'list_price': 180.0,
            'type': 'product',
        })

    def test_create_purchase_order(self):
        """Check a purchase user can create a vendor bill from a purchase order but not post it"""
        purchase_order_form = Form(self.env['purchase.order'].with_user(self.purchase_user))
        purchase_order_form.partner_id = self.vendor
        with purchase_order_form.order_line.new() as line:
            line.name = self.product.name
            line.product_id = self.product
            line.product_qty = 4
            line.price_unit = 5

        purchase_order = purchase_order_form.save()

        # purchase_order.order_line.qty_received = 4
        # purchase_order.action_create_invoice()
        # invoice = purchase_order.invoice_ids
        # with self.assertRaises(AccessError):
        #     invoice.action_post()


    def test_force_delivery_status_with_user_allowed(self):
        cls.purchase_user.write({'groups_id': [(4, group_system.id)]})
        purchase_order.write({'force_delivered_status' : 'received'})
        self.assertEqual(purchase_order.delivery_status, 'received')

    def test_force_delivery_status_without_user_allowed(self):
        cls.purchase_user.write({'groups_id': [(3, group_system.id)]})
        with self.assertRaises(AccessError):
            purchase_order.write({'force_delivered_status' : 'received'})
        # self.assertEqual(purchase_order.delivery_status, 'received')

    def test_confirm_order(self):
        purchase_order.internal_note = 'lo que sea'
        purchase_order.button_confirm()
        self.assertEqual(purchase_order.picking_ids.note, purchase_order.internal_note)
