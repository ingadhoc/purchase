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

    def test_forced_invoiced_status_on_lines(self):
        """La OC forzada a facturada mantiene ese estado en sus líneas."""
        self.env.user.groups_id |= self.env.ref("base.group_system")
        self.purchase_order.force_invoiced_status = "invoiced"
        self.assertEqual(self.purchase_order.order_line.invoice_status, "invoiced")

    def test_unlink_line_with_done_dest_move(self):
        """Borrar una línea de OC cuya entrega destino ya está 'done' no debe fallar.

        Reproduce el caso MTO en el que la venta se entregó desde stock disponible
        (movimiento destino en 'done') y luego se quiere eliminar la línea de la OC
        que la abastecía. El unlink estándar de purchase_stock intentaría cancelar
        ese movimiento ya hecho y lanzaría UserError; con el fix se desvincula en
        lugar de cancelarlo.
        """
        draft_po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 5,
                            "price_unit": 50,
                        }
                    ),
                ],
            }
        )
        pol = draft_po.order_line
        pol.propagate_cancel = True

        done_move = self.env["stock.move"].create(
            {
                "name": "Test delivery move",
                "product_id": self.product.id,
                "product_uom_qty": 5,
                "product_uom": self.product.uom_id.id,
                "location_id": self.env.ref("stock.stock_location_stock").id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            }
        )
        done_move.write({"state": "done"})
        pol.move_dest_ids = [Command.link(done_move.id)]

        # No debe lanzar UserError por el movimiento 'Hecho'.
        pol.unlink()

        # El movimiento entregado debe quedar intacto.
        self.assertEqual(done_move.state, "done")
        self.assertFalse(draft_po.order_line)
