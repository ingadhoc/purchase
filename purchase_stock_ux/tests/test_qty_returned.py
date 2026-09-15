from odoo import Command
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestQtyReturned(PurchaseTestCommon):
    """Cobertura de qty_returned (_compute_qty_returned) en compras.

    Ticket 126775: se recibió el producto equivocado, se lo devolvió al proveedor marcando
    "Para abonar" y se corrigió el producto en la misma línea de la OC. La devolución del
    producto viejo se descontaba de lo pendiente a facturar del producto nuevo, dejando la
    OC como "totalmente facturada" con cero facturado y sin forma de emitir la factura del
    proveedor. El cómputo debe considerar solo los movimientos del producto de la línea,
    igual que _compute_qty_received del core.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Qty Returned Vendor"})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.warehouse.reception_steps = "one_step"

    # ------------------------------------------------------------------ helpers
    def _product(self, name):
        return self.env["product.product"].create(
            {
                "name": name,
                "type": "consu",
                "is_storable": True,
                "purchase_method": "purchase",
            }
        )

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

    def _validate(self, picking):
        picking.action_assign()
        for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.button_validate()

    def _receive_all(self, po):
        for picking in po.picking_ids.filtered(lambda p: p.state not in ("done", "cancel")):
            self._validate(picking)

    def _return_all(self, po, qty, to_refund=True):
        receipt = po.picking_ids.filtered(lambda p: p.picking_type_id.code == "incoming" and p.state == "done").sorted(
            "id"
        )[-1:]
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=receipt.id, active_model="stock.picking", active_ids=receipt.ids)
            .create({})
        )
        for wizard_line in wizard.product_return_moves:
            wizard_line.quantity = qty
            wizard_line.to_refund = to_refund
        action = wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])
        self._validate(return_picking)
        return return_picking

    # -------------------------------------------------------------------- tests
    def test_return_of_replaced_product_not_counted(self):
        """Ticket 126775: la devolución del producto reemplazado no debe contar como devuelta
        en la línea -que ahora tiene otro producto- ni bloquear su facturación."""
        old_product = self._product("QR producto viejo")
        new_product = self._product("QR producto nuevo")
        po = self._confirm_po(old_product, 10)
        line = po.order_line
        self._receive_all(po)
        self._return_all(po, 10, to_refund=True)

        line.product_id = new_product
        line.invalidate_recordset()
        # el cambio de producto no está en los depends de los campos almacenados
        line._compute_qty_invoiced()
        line._compute_invoice_status()

        self.assertEqual(line.qty_returned, 0, "la devolución del producto viejo se contó en la línea nueva")
        self.assertEqual(line.qty_to_invoice, 10, "la línea quedó sin cantidad pendiente a facturar")
        self.assertEqual(line.invoice_status, "to invoice")

    def test_return_of_same_product_counted(self):
        """No regresión: la devolución del mismo producto de la línea sí debe seguir contando."""
        product = self._product("QR mismo producto")
        po = self._confirm_po(product, 10)
        line = po.order_line
        self._receive_all(po)
        self._return_all(po, 10, to_refund=True)

        line.invalidate_recordset()
        self.assertEqual(line.qty_returned, 10)
        self.assertEqual(line.qty_to_invoice, 0)
