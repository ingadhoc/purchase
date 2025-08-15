from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestPurchaseOrder(PurchaseTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
            }
        )

        cls.purchase_order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_qty": 10,
                            "price_unit": 100,
                        }
                    ),
                ],
                "internal_notes": "Test internal notes",
            }
        )

        cls.purchase_order.button_confirm()
