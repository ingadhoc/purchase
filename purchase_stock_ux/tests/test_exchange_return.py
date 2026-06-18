##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestExchangeReturn(PurchaseTestCommon):
    """Reproduce el flujo del video de la tarea 65271: devolución para cambio en compras.

    Pedido de 10, recepción de 10, devolución para cambio de 4 (sin 'a abonar') y
    recepción de la reposición de 4. La cantidad recibida debe quedar en 10 (no 14).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product.type = "consu"
        cls.product.is_storable = True

        cls.partner = cls.env["res.partner"].create({"name": "Test Partner Exchange"})
        cls.po = cls.env["purchase.order"].create(
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
            }
        )
        cls.po.button_confirm()
        cls.line = cls.po.order_line

    def _validate(self, picking):
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.move_ids.picked = True
        picking.button_validate()

    def test_exchange_return_keeps_received_qty(self):
        # 1) Recepción completa de 10
        receipt = self.po.picking_ids
        self._validate(receipt)
        self.assertEqual(self.line.qty_received, 10.0)

        # 2) Devolución para cambio de 4 (to_refund=False), genera salida + entrada de reposición
        return_wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=receipt.id, active_model="stock.picking")
            .create({})
        )
        return_wizard.product_return_moves.write({"quantity": 4.0, "to_refund": False})
        action = return_wizard.action_create_exchanges()

        return_picking = receipt.return_ids
        self.assertTrue(return_picking, "Debería haberse creado el albarán de devolución (salida)")
        self.assertTrue(
            all(return_picking.move_ids.mapped("is_exchange_move")),
            "Los movimientos de la devolución para cambio deben marcarse is_exchange_move",
        )
        self._validate(return_picking)

        # La devolución para cambio no es 'a abonar': no impacta la columna de devueltos
        self.assertEqual(self.line.qty_returned, 0.0)
        # Tras devolver pero antes de recibir la reposición, sigue en 10 (semántica de no-reembolso)
        self.assertEqual(self.line.qty_received, 10.0)

        # 3) Recepción de la reposición de 4 (albarán de entrada del cambio)
        exchange_in = self.env["stock.picking"].browse(action["res_id"])
        self.assertTrue(
            all(exchange_in.move_ids.mapped("is_exchange_move")),
            "Los movimientos de reposición del cambio deben marcarse is_exchange_move",
        )
        self._validate(exchange_in)

        # 4) Verificación central: la cantidad recibida NO debe superar lo pedido
        self.assertEqual(
            self.line.qty_received,
            10.0,
            "Tras la devolución para cambio + reposición, la cantidad recibida debe quedar en 10, no en 14",
        )
