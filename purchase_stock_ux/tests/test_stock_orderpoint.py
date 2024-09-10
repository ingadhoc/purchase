from odoo.addons.stock.tests.common import TestStockCommon
from odoo import Command


class TestStockOrderpoint(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({
                'name': 'Main Supplier',
            })

        cls.product = cls.env['product.product'].create({
            'name': 'Test Product with Supplier',
            'seller_ids': [Command.create({'partner_id': cls.partner.id})],
        })

        cls.location_stock = cls.env.ref('stock.stock_location_stock')

        cls.orderpoint = cls.env['stock.warehouse.orderpoint'].create({
            'product_id': cls.product.id,
            'location_id' : cls.location_stock.id,
            'product_min_qty' : 10,
        })


    def test_get_orderpoint_values_with_default_supplier(self):
        """
        Test the main seller is set as a the default supplier in replenishment rules.
        """
        # In stock_orderpoint model, the method _get_orderpoint_action(self) calls _get_orderpoint_values.
        values = self.orderpoint._get_orderpoint_values(self.product.id,self.location_stock.id)
        self.assertEqual(values['supplier_id'],self.product.seller_ids[0].id, "The main seller should be set as the supplier in replenishment rules")
