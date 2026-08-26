from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestCancelRemaining(PurchaseTestCommon):
    """Cobertura de "Cancelar remanente" (button_cancel_remaining) en compras.

    Al cancelar remanente NO debe quedar (ni generarse) recepción pendiente del proveedor:
      * Ticket 124773: tras una devolución con reembolso quedaba un IN pendiente vivo, inflando
        el pronóstico de unidades a recibir.
      * Ticket 124957: cuando el move negativo no neteaba, se generaba una contra-entrega (OUT) al
        proveedor en lugar de cancelar el remanente.

    Se valida en recepción de 1, 2 y 3 pasos: el remanente vive siempre en el move de primer paso
    (proveedor->entrada) y debe quedar cancelado, preservando lo ya recibido en tránsito a stock.
    """

    STEPS = ("one_step", "two_steps", "three_steps")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Cancel Remaining Vendor"})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)

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

    def _chain(self, line):
        """Toda la cadena de moves de la línea (en 2/3 pasos los internos cuelgan por move_dest_ids)."""
        line.invalidate_recordset()
        chain = frontier = line.move_ids
        while frontier:
            frontier = (frontier.move_dest_ids | frontier.move_orig_ids) - chain
            chain |= frontier
        return chain

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

    def _receive_full(self, po):
        """Recibe la cantidad pedida hasta stock, empujando toda la cadena (1/2/3 pasos)."""
        for _i in range(8):
            pickings = po.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
            for picking in pickings:
                picking.action_assign()
            ready = pickings.filtered(lambda p: p.state in ("assigned", "partially_available"))
            if not ready:
                break
            for picking in ready:
                self._validate(picking)

    def _receive_partial_at_input(self, po, qty):
        """Recibe parcialmente en el primer picking (proveedor->entrada) y deja backorder."""
        picking = po.picking_ids.filtered(
            lambda p: p.picking_type_id.code == "incoming" and p.state not in ("done", "cancel")
        ).sorted("id")[:1]
        self._validate(picking, qty=qty, backorder=True)

    def _return(self, po, qty, to_refund=True, validate=True):
        receipt = po.picking_ids.filtered(lambda p: p.picking_type_id.code == "incoming" and p.state == "done").sorted(
            "id"
        )[-1:]
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=receipt.id, active_model="stock.picking", active_ids=receipt.ids)
            .create({})
        )
        for line in wizard.product_return_moves:
            line.quantity = qty
            line.to_refund = to_refund
        action = wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])
        if validate:
            self._validate(return_picking)
        return return_picking

    # -------------------------------------------------------------- assertions
    def _assert_no_vendor_pending(self, line):
        """No debe quedar recepción pendiente DEL PROVEEDOR ni contra-entrega al proveedor."""
        chain = self._chain(line)
        vendor_pending = chain.filtered(
            lambda m: m.state not in ("done", "cancel")
            and m.location_id.usage == "supplier"
            and not m._is_exchange_move_helper()
        )
        self.assertFalse(vendor_pending, "quedó recepción pendiente del proveedor tras cancelar remanente")
        out_to_vendor = chain.filtered(
            lambda m: m.state not in ("done", "cancel")
            and m.location_dest_id.usage == "supplier"
            and not m._is_exchange_move_helper()
        )
        self.assertFalse(out_to_vendor, "quedó una contra-entrega (OUT) al proveedor tras cancelar remanente")
        self.assertAlmostEqual(line.product_qty, line.qty_received + line.qty_returned)

    # -------------------------------------------------------------------- tests
    def test_partial_receipt_cancel_remaining(self):
        """Caso base sin devoluciones: recibir parcial y cancelar remanente cierra la línea, en 1/2/3 pasos."""
        for steps in self.STEPS:
            with self.subTest(steps=steps):
                self.warehouse.reception_steps = steps
                product = self._product("CR base %s" % steps)
                po = self._confirm_po(product, 6)
                line = po.order_line
                self._receive_partial_at_input(po, 2)
                line.button_cancel_remaining()
                self._assert_no_vendor_pending(line)
                self.assertEqual(line.product_qty, 2)

    def test_return_refund_then_cancel_remaining(self):
        """Ticket 124773: recibir todo, devolver con reembolso, subir la cantidad y cancelar remanente
        no debe dejar (ni inflar) el IN pendiente, en 1/2/3 pasos."""
        for steps in self.STEPS:
            with self.subTest(steps=steps):
                self.warehouse.reception_steps = steps
                product = self._product("CR 124773 %s" % steps)
                po = self._confirm_po(product, 4)
                line = po.order_line
                self._receive_full(po)
                self._return(po, 4, to_refund=True)
                line.invalidate_recordset()
                line.product_qty = 6
                line.button_cancel_remaining()
                self._assert_no_vendor_pending(line)

    def test_open_return_not_cancelled(self):
        """Una devolución al proveedor ABIERTA (sin validar) no es parte del remanente y NO debe
        cancelarse al cancelar remanente (arista reportada en base cummotors: cancelaba todo)."""
        for to_refund in (True, False):
            with self.subTest(to_refund=to_refund):
                self.warehouse.reception_steps = "one_step"
                product = self._product("CR open return %s" % to_refund)
                po = self._confirm_po(product, 10)
                line = po.order_line
                self._receive_partial_at_input(po, 6)  # deja backorder de 4 = remanente a cancelar
                open_return = self._return(po, 2, to_refund=to_refund, validate=False)
                self.assertNotIn(open_return.state, ("done", "cancel"))
                line.button_cancel_remaining()
                open_return.invalidate_recordset()
                self.assertNotEqual(
                    open_return.state, "cancel", "cancelar remanente canceló una devolución abierta en curso"
                )
                self.assertTrue(
                    open_return.move_ids.filtered(lambda m: m.state != "cancel"),
                    "el move de la devolución abierta quedó cancelado",
                )
                # el remanente forward del proveedor (backorder de 4) sí debe cancelarse
                forward_pending = self._chain(line).filtered(
                    lambda m: m.state not in ("done", "cancel")
                    and m.location_id.usage == "supplier"
                    and not m.origin_returned_move_id
                )
                self.assertFalse(forward_pending, "no se canceló el remanente forward del proveedor")

    def test_received_goods_preserved(self):
        """Cancelar remanente no debe cancelar lo ya recibido: en 2/3 pasos el tránsito interno sobrevive."""
        self.warehouse.reception_steps = "two_steps"
        product = self._product("CR preserva")
        po = self._confirm_po(product, 6)
        line = po.order_line
        self._receive_partial_at_input(po, 2)
        line.button_cancel_remaining()
        chain = self._chain(line)
        internal_alive = chain.filtered(
            lambda m: m.state not in ("done", "cancel")
            and m.location_id.usage in ("internal", "transit")
            and m.location_dest_id.usage in ("internal", "transit")
        )
        self.assertTrue(internal_alive, "se canceló por error la mercadería recibida en tránsito a stock")
        self.assertAlmostEqual(sum(internal_alive.mapped("product_uom_qty")), 2)
