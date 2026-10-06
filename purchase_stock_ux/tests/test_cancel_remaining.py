from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon
from odoo.exceptions import UserError


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

    def _subcontracted_product(self, name):
        """Storable product with a subcontracting BoM (subcontractor: self.partner) whose component
        is resupplied on order. Skips the test when mrp_subcontracting is not installed."""
        resupply_route = self.env.ref("mrp_subcontracting.route_resupply_subcontractor_mto", raise_if_not_found=False)
        if not resupply_route:
            self.skipTest("mrp_subcontracting is not installed")
        component = self._product("%s component" % name)
        component.route_ids = [Command.link(resupply_route.id)]
        finished = self._product(name)
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "type": "subcontract",
                "subcontractor_ids": [Command.link(self.partner.id)],
                "bom_line_ids": [Command.create({"product_id": component.id, "product_qty": 1})],
            }
        )
        return finished, bom

    def _open_moves_of_order(self, po, exclude=None):
        return self.env["stock.move"].search(
            [("group_id", "=", po.group_id.id), ("state", "not in", ("done", "cancel"))]
        ) - (exclude or self.env["stock.move"])

    def test_subcontracted_cancel_remaining_nothing_received(self):
        """Subcontracting: cancel remaining with nothing received must not raise and must cancel the
        whole receipt chain (1/2/3 steps), the subcontracting MO and the resupply, so the line can be
        re-ordered with the new BoM."""
        for steps in self.STEPS:
            with self.subTest(steps=steps):
                self.warehouse.reception_steps = steps
                finished, bom = self._subcontracted_product("CR subcontract %s" % steps)
                po = self._confirm_po(finished, 10)
                line = po.order_line
                production = self.env["mrp.production"].search([("product_id", "=", finished.id)])
                resupply = production.picking_ids
                self.assertTrue(resupply, "no resupply picking was created for the subcontracting MO")
                # the BoM changes after the order was confirmed
                new_comp = self._product("CR subcontract new component %s" % steps)
                bom.bom_line_ids = [Command.clear(), Command.create({"product_id": new_comp.id, "product_qty": 1})]

                line.button_cancel_remaining()

                self.assertEqual(line.product_qty, 0)
                self.assertFalse(self._open_moves_of_order(po), "a receipt leg was left open")
                self.assertEqual(production.state, "cancel")
                self.assertEqual(resupply.state, "cancel")

                # ordering again takes the current BoM
                line.product_qty = 10
                new_production = self.env["mrp.production"].search(
                    [("product_id", "=", finished.id), ("state", "!=", "cancel")]
                )
                self.assertEqual(new_production.move_raw_ids.product_id, new_comp)

    def test_subcontracted_recorded_production_blocks_cancel_remaining(self):
        """If the subcontractor already recorded production, cancel remaining stops with a message
        instead of cancelling the MO and losing what was recorded."""
        self.warehouse.reception_steps = "one_step"
        finished, _bom = self._subcontracted_product("CR subcontract recorded")
        po = self._confirm_po(finished, 10)
        line = po.order_line
        production = self.env["mrp.production"].search([("product_id", "=", finished.id)])
        production.subcontracting_has_been_recorded = True

        with self.assertRaisesRegex(UserError, production.name):
            line.button_cancel_remaining()
        self.assertEqual(line.product_qty, 10)
        self.assertNotEqual(production.state, "cancel")

    def test_subcontracted_partial_receipt_cancel_remaining(self):
        """Subcontracting with a partial receipt: cancel remaining cancels the pending receipt and its
        MO, and keeps the internal legs (2/3 steps) that bring the received goods to stock."""
        for steps in self.STEPS:
            with self.subTest(steps=steps):
                self.warehouse.reception_steps = steps
                finished, _bom = self._subcontracted_product("CR subcontract partial %s" % steps)
                po = self._confirm_po(finished, 10)
                line = po.order_line
                self._receive_partial_at_input(po, 4)

                line.button_cancel_remaining()

                self.assertEqual(line.product_qty, 4)
                self.assertFalse(
                    self._open_moves_of_order(po).filtered("purchase_line_id"), "the pending receipt was left open"
                )
                self.assertFalse(
                    self.env["mrp.production"].search(
                        [("product_id", "=", finished.id), ("state", "not in", ("done", "cancel"))]
                    ),
                    "the MO of the pending quantity was left open",
                )
                internal_alive = self._open_moves_of_order(po).filtered(
                    lambda m: m.location_id.usage == "internal" and m.location_dest_id.usage == "internal"
                )
                if steps == "one_step":
                    self.assertFalse(internal_alive)
                else:
                    self.assertAlmostEqual(sum(internal_alive.mapped("product_uom_qty")), 4)

    def test_subcontracted_refunded_return_cancel_remaining(self):
        """Subcontracting with a refunded return: cancel remaining closes the line without creating
        (and cancelling) a new receipt and MO for the returned quantity."""
        self.warehouse.reception_steps = "one_step"
        finished, _bom = self._subcontracted_product("CR subcontract refund")
        po = self._confirm_po(finished, 10)
        line = po.order_line
        self._receive_partial_at_input(po, 4)
        self._return(po, 2, to_refund=True)
        line.invalidate_recordset()
        productions = self.env["mrp.production"].search([("product_id", "=", finished.id)])
        pickings = po.picking_ids

        line.button_cancel_remaining()

        self.assertEqual(line.product_qty, line.qty_received + line.qty_returned)
        self.assertFalse(
            self._open_moves_of_order(po).filtered("purchase_line_id"), "the pending receipt was left open"
        )
        self.assertEqual(self.env["mrp.production"].search([("product_id", "=", finished.id)]), productions)
        self.assertEqual(po.picking_ids, pickings)

    def test_subcontracted_cancel_remaining_keeps_sale_delivery(self):
        """Subcontracting bought on order for a sale: cancel remaining on the purchase cancels the
        receipt chain (1/2/3 steps) but not the customer delivery, as core's netting does not either."""
        if "sale_line_id" not in self.env["stock.move"]._fields:
            self.skipTest("sale_stock is not installed")
        self.warehouse.delivery_steps = "ship_only"
        mto_route = self.warehouse.mto_pull_id.route_id
        mto_route.active = True
        for steps in self.STEPS:
            with self.subTest(steps=steps):
                self.warehouse.reception_steps = steps
                # the purchase line takes it from the buy rule; with it on, a plain cancel would reach the delivery
                self.warehouse.buy_pull_id.propagate_cancel = True
                finished, _bom = self._subcontracted_product("CR subcontract MTO %s" % steps)
                finished.route_ids = [
                    Command.link(mto_route.id),
                    Command.link(self.warehouse.buy_pull_id.route_id.id),
                ]
                finished.seller_ids = [Command.create({"partner_id": self.partner.id, "price": 10.0})]
                sale = self.env["sale.order"].create(
                    {
                        "partner_id": self.env["res.partner"].create({"name": "CR customer"}).id,
                        "order_line": [Command.create({"product_id": finished.id, "product_uom_qty": 5})],
                    }
                )
                sale.action_confirm()
                delivery_move = sale.order_line.move_ids
                line = self.env["purchase.order.line"].search([("product_id", "=", finished.id)])
                self.assertEqual(len(line), 1, "the sale did not generate the purchase to the subcontractor")
                line.order_id.button_confirm()
                self.assertTrue(line.propagate_cancel)
                self.assertIn(delivery_move, self._chain(line))

                line.button_cancel_remaining()

                self.assertFalse(
                    self._open_moves_of_order(line.order_id, exclude=delivery_move), "a receipt leg was left open"
                )
                self.assertNotEqual(delivery_move.state, "cancel", "cancel remaining cancelled the customer delivery")
