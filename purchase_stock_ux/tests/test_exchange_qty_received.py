from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestExchangeQtyReceived(PurchaseTestCommon):
    """Una devolucion para cambio en una recepcion no debe cambiar lo recibido de la OC."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Exchange Vendor"})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.warehouse.reception_steps = "one_step"

    def _product(self, purchase_method):
        return self.env["product.product"].create(
            {
                "name": f"Exchange product {purchase_method}",
                "type": "consu",
                "is_storable": True,
                "purchase_method": purchase_method,
            }
        )

    def _validate(self, picking):
        picking.action_assign()
        for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.button_validate()

    def _received_and_invoiced_po(self, product, qty=10):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.warehouse.in_type_id.id,
                "order_line": [Command.create({"product_id": product.id, "product_qty": qty, "price_unit": 10.0})],
            }
        )
        po.button_confirm()
        self._validate(po.picking_ids)
        po.action_create_invoice()
        po.invoice_ids.invoice_date = po.date_order
        po.invoice_ids.action_post()
        return po

    def _exchange(self, po, qty, to_refund):
        receipt = po.picking_ids.filtered(lambda p: p.state == "done")
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=receipt.id, active_model="stock.picking", active_ids=receipt.ids)
            .create({})
        )
        wizard.product_return_moves.quantity = qty
        wizard.product_return_moves.to_refund = to_refund
        wizard.action_create_exchanges()
        for picking in po.picking_ids.filtered(lambda p: p.state not in ("done", "cancel")):
            self._validate(picking)
        self.assertEqual(len(po.picking_ids.filtered(lambda p: p.state == "done")), 3)

    def test_exchange_without_refund(self):
        """Cambio con "Para abonar" destildado: 10 recibidas y nada pendiente de facturar."""
        for purchase_method in ("receive", "purchase"):
            with self.subTest(purchase_method=purchase_method):
                po = self._received_and_invoiced_po(self._product(purchase_method))
                self._exchange(po, 1, to_refund=False)
                line = po.order_line
                self.assertEqual(line.qty_received, 10)
                self.assertEqual(line.qty_returned, 0)
                self.assertEqual(line.qty_to_invoice, 0)

    def test_exchange_with_refund(self):
        """Cambio con "Para abonar" tildado: la devolucion resta y la reposicion suma."""
        po = self._received_and_invoiced_po(self._product("receive"))
        self._exchange(po, 1, to_refund=True)
        self.assertEqual(po.order_line.qty_received, 10)
