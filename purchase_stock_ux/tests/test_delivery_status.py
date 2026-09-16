from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon
from odoo.tests import Form


class TestDeliveryStatus(PurchaseTestCommon):
    """Cobertura de delivery_status (_compute_delivery_status) en compras.

    Ticket 128102: se recibió uno de los traslados de la orden y se canceló el otro, y la orden
    seguía "A recibir" porque el cómputo mira solo cantidades. Lo que quedó en un traslado
    cancelado nunca va a llegar, así que la línea está cerrada. El criterio propio -que separa
    una recepción parcial validada de una orden completa- se mantiene.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Delivery Status Vendor"})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.warehouse.reception_steps = "one_step"

    # ------------------------------------------------------------------ helpers
    def _confirm_po(self):
        product = self.env["product.product"].create(
            {
                "name": "DS product",
                "type": "consu",
                "is_storable": True,
            }
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.warehouse.in_type_id.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 10,
                            "price_unit": 10.0,
                            "name": product.name,
                        }
                    )
                ],
            }
        )
        po.button_confirm()
        return po

    def _receive(self, po, qty, backorder=True):
        picking = po.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
        picking.action_assign()
        for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            move.quantity = qty
            move.picked = True
        action = picking.button_validate()
        if isinstance(action, dict) and action.get("res_model") == "stock.backorder.confirmation":
            wizard = Form(self.env[action["res_model"]].with_context(**action["context"])).save()
            if backorder:
                wizard.process()
            else:
                wizard.process_cancel_backorder()

    def _assert_status(self, po, status):
        self.assertEqual(po.order_line.delivery_status, status)
        self.assertEqual(po.delivery_status, status)

    # -------------------------------------------------------------------- tests
    def test_cancelled_receipt_is_received(self):
        """Ticket 128102: con la única recepción cancelada no queda nada por recibir."""
        po = self._confirm_po()
        po.picking_ids.action_cancel()

        self._assert_status(po, "received")

    def test_cancelled_backorder_is_received(self):
        """Recibido en parte y el remanente cancelado: tampoco queda nada por recibir."""
        po = self._confirm_po()
        self._receive(po, 4)
        backorder = po.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
        backorder.action_cancel()

        self.assertEqual(po.order_line.qty_received, 4)
        self._assert_status(po, "received")

    def test_open_receipt_is_to_receive(self):
        po = self._confirm_po()

        self._assert_status(po, "to receive")

    def test_partial_receipt_without_backorder_is_to_receive(self):
        """No regresión: validar de menos sin backorder deja el movimiento hecho, no cancelado,
        así que la línea sigue a recibir y conserva el botón de cancelar remanente."""
        po = self._confirm_po()
        self._receive(po, 4, backorder=False)

        self.assertEqual(po.order_line.qty_received, 4)
        self._assert_status(po, "to receive")

    def test_new_receipt_after_cancel_is_to_receive(self):
        """Volver a pedir la recepción deja un movimiento vivo."""
        po = self._confirm_po()
        po.picking_ids.action_cancel()
        po._create_picking()

        self._assert_status(po, "to receive")
