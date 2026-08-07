from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestCancelRemaining(PurchaseTestCommon):
    """Cobertura de "Cancelar remanente" (button_cancel_remaining) en compras.

    Foco del ticket 124773: cuando hubo una devolución con reembolso, cancelar remanente debe dejar la
    línea cerrada y SIN recepción pendiente (antes inflaba el IN pendiente y quedaba vivo en el pronóstico).
    Sumamos el caso base sin devoluciones (recepción parcial + cancelar remanente).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Cancel Remaining Vendor"})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.warehouse.reception_steps = "one_step"

    # ------------------------------------------------------------------ helpers
    def _product(self, name):
        return self.env["product.product"].create({"name": name, "type": "consu", "is_storable": True})

    def _confirm_po(self, product, qty):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.warehouse.in_type_id.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "price_unit": 10.0,
                            "name": product.name,
                        }
                    )
                ],
            }
        )
        po.button_confirm()
        return po

    def _reception_pickings(self, product):
        """Pickings que ingresan el producto a ubicaciones internas (la cadena de recepción, que en
        2/3 pasos no cuelga de ``po.picking_ids``)."""
        moves = self.env["stock.move"].search([("product_id", "=", product.id), ("picking_id", "!=", False)])
        return moves.filtered(lambda m: m.location_dest_id.usage in ("internal", "transit")).picking_id

    def _validate(self, picking, qty=None, backorder=True):
        if picking.state not in ("assigned", "partially_available"):
            picking.action_assign()
        for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            move.quantity = move.product_uom_qty if qty is None else qty
            move.picked = True
        res = picking.button_validate()
        if isinstance(res, dict) and res.get("res_model") == "stock.backorder.confirmation":
            wizard = self.env[res["res_model"]].with_context(**res["context"]).create({})
            wizard.process() if backorder else wizard.process_cancel_backorder()

    def _receive_full(self, product):
        for _i in range(8):
            pickings = self._reception_pickings(product).filtered(lambda p: p.state not in ("done", "cancel"))
            for picking in pickings.filtered(lambda p: p.state not in ("assigned", "partially_available")):
                picking.action_assign()
            ready = pickings.filtered(lambda p: p.state in ("assigned", "partially_available"))
            if not ready:
                break
            for picking in ready:
                self._validate(picking)

    def _receive_partial(self, po, qty):
        picking = po.picking_ids.filtered(
            lambda p: p.picking_type_id.code == "incoming" and p.state not in ("done", "cancel")
        )[:1]
        self._validate(picking, qty=qty, backorder=True)

    def _return(self, picking, qty, to_refund=True):
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_model="stock.picking", active_ids=picking.ids)
            .create({})
        )
        for line in wizard.product_return_moves:
            line.quantity = qty
            line.to_refund = to_refund
        action = wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])
        self._validate(return_picking)
        return return_picking

    def _open_reception_moves(self, line):
        """Moves de recepción todavía abiertos (toda la cadena), sin contar reemplazos de cambio."""
        line.invalidate_recordset()
        chain = frontier = line.move_ids
        seen = line.move_ids
        while frontier:
            frontier = frontier.move_dest_ids - seen
            chain |= frontier
            seen |= frontier
        return chain.filtered(
            lambda m: m.state not in ("done", "cancel")
            and m.location_dest_id.usage in ("internal", "transit")
            and not m._is_exchange_move_helper()
        )

    def _assert_line_closed(self, line):
        line.invalidate_recordset()
        self.assertFalse(self._open_reception_moves(line), "quedó recepción pendiente tras cancelar remanente")
        self.assertEqual(line.delivery_status, "received")
        self.assertAlmostEqual(line.product_qty, line.qty_received + line.qty_returned)

    # -------------------------------------------------------------------- tests
    def test_return_refund_then_cancel_remaining(self):
        """Ticket 124773: recibir todo, devolver con reembolso, subir la cantidad y cancelar remanente
        no debe dejar (ni inflar) el IN pendiente."""
        product = self._product("CR ticket 124773")
        po = self._confirm_po(product, 4)
        line = po.order_line
        self._receive_full(product)
        receipt = self._reception_pickings(product).filtered(lambda p: p.state == "done").sorted("id")[:1]
        self._return(receipt, 4, to_refund=True)
        line.invalidate_recordset()
        line.product_qty = 6
        line.button_cancel_remaining()
        self._assert_line_closed(line)

    def test_partial_receipt_cancel_remaining(self):
        """Caso base sin devoluciones: recibir parcial y cancelar remanente cierra la línea."""
        product = self._product("CR base")
        po = self._confirm_po(product, 6)
        line = po.order_line
        self._receive_partial(po, 2)
        line.button_cancel_remaining()
        self._assert_line_closed(line)
        self.assertEqual(line.product_qty, 2)

    # TODO: devolución con cambio (is_exchange_move) — el fix excluye el reemplazo esperado, pero armar
    # el reemplazo de forma estable dentro de TransactionCase requiere más setup; queda como follow-up.
