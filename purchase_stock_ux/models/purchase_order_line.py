##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    receipt_status = fields.Selection(
        [
            ("pending", "Not Received"),
            ("partial", "Partially Received"),
            ("full", "Fully Received"),
        ],
        compute="_compute_receipt_status",
        store=True,
        readonly=True,
        copy=False,
    )

    vouchers = fields.Char(compute="_compute_vouchers")

    qty_on_voucher = fields.Float(
        compute="_compute_qty_on_voucher",
        string="On Voucher",
        digits="Product Unit",
    )

    qty_returned = fields.Float(
        string="Returned", copy=False, default=0.0, readonly=True, compute="_compute_qty_returned"
    )

    @api.depends_context("voucher")
    def _compute_qty_on_voucher(self):
        # al calcular por voucher no tenemos en cuenta el metodo de facturacion
        # es decir, que calculamos como si fuese metodo segun lo recibido
        voucher = self.env.context.get("voucher", False)
        if not voucher:
            self.update({"qty_on_voucher": 0.0})
            return
        lines = self.filtered(lambda x: x.order_id.state in ["purchase", "done"])
        moves = self.env["stock.move"].search(
            [
                ("id", "in", lines.mapped("move_ids").ids),
                ("state", "=", "done"),
                ("picking_id.vouchers", "ilike", voucher[0]),
            ]
        )
        for line in lines:
            line.qty_on_voucher = sum(moves.filtered(lambda x: x.id in line.move_ids.ids).mapped("product_uom_qty"))

    def unlink(self):
        """Evitar el bloqueo al borrar líneas MTO cuya entrega ya se hizo.

        El unlink estándar de ``purchase_stock`` cancela los ``move_dest_ids`` de
        las líneas con ``propagate_cancel`` sin filtrar los movimientos ya
        realizados. Si el destino -la entrega al cliente de una línea MTO- ya
        está en estado ``done`` (porque se entregó desde stock disponible),
        ``stock.move._action_cancel()`` lanza "No puede cancelar un movimiento de
        existencias que se haya configurado como 'Hecho'" y bloquea el borrado.

        ``purchase.order.button_cancel()`` ya contempla este caso filtrando los
        movimientos ``state != 'done'`` antes de cancelar; replicamos esa misma
        protección acá: desvinculamos los movimientos destino ya hechos para que
        el borrado no intente cancelarlos. El movimiento entregado queda intacto.
        """
        for line in self:
            done_dest_moves = line.move_dest_ids.filtered(lambda m: m.state == "done")
            if done_dest_moves:
                line.move_dest_ids = [fields.Command.unlink(move.id) for move in done_dest_moves]
        return super().unlink()

    def button_cancel_remaining(self):
        # la cancelación de kits no está bien resuelta ya que odoo
        # solo computa la cantidad entregada cuando todo el kit se entregó.
        # Cuestión que, por ahora, desactivamos la cancelación de kits.

        bom_enable = "bom_ids" in self.env["product.template"]._fields
        for rec in self:
            old_product_qty = rec.product_qty
            # TODO tal vez cambiar en v10
            # en este caso si lo bloqueamos ya que si llegan a querer generar
            # nc lo pueden hacer con el buscar líneas de las facturas
            # y luego lo pueden terminar cancelando
            if rec.qty_invoiced > rec.qty_received:
                raise UserError(
                    _(
                        "You can not cancel remianing qty to receive because "
                        "there are more product invoiced than the received. "
                        "You should correct invoice or ask for a refund"
                    )
                )
            if bom_enable:
                bom = self.env["mrp.bom"]._bom_find(products=rec.product_id)[rec.product_id]
                if bom and bom.type == "phantom":
                    raise UserError(
                        _("Cancel remaining can't be called for Kit Products (products with a bom of type kit).")
                    )
            # Subcontracting: once core nets the negative move, mrp_subcontracting runs action_assign
            # on the emptied receipt and raises. Cancel the remainder first so no negative move is
            # created; like core's netting, don't propagate the cancel to destination moves.
            subcontracted_moves = rec._get_remaining_moves_to_cancel().filtered(
                lambda m: "is_subcontract" in m._fields and m.is_subcontract
            )
            if subcontracted_moves:
                # The MO is the subcontractor's: a purchase user may not have manufacturing access
                subcontracted_moves = subcontracted_moves.sudo()
                recorded_productions = subcontracted_moves._get_subcontract_production().filtered(
                    lambda p: p.state in ("progress", "to_close")
                )
                if recorded_productions:
                    raise UserError(
                        _(
                            "The subcontractor already recorded production on %(productions)s. "
                            "Receive what was produced or cancel that manufacturing order before "
                            "cancelling the remaining quantity.",
                            productions=", ".join(recorded_productions.mapped("name")),
                        )
                    )
                # With refunded returns the negative move does not empty the receipt, and cancelling
                # first would make core create a new receipt (and MO) for the returned quantity.
                if rec.uom_id.is_zero(rec.qty_returned):
                    subcontracted_moves.write({"propagate_cancel": False})
                    subcontracted_moves.with_context(cancel_from_order=True)._action_cancel()
            if not rec._get_remaining_moves_to_cancel():
                rec = rec.with_context(cancel_remaining_line_ids=rec.ids)
            rec.with_context(cancel_from_order=True).product_qty = rec.qty_received + rec.qty_returned
            # Bajar product_qty hace que Odoo (>=16) reduzca los moves, pero no siempre cancela el
            # remanente de recepción: si hubo una devolución con reembolso, o si el move negativo no
            # netea contra el pendiente (precio/ubicación final distintos), queda una recepción viva en
            # el pronóstico (o una contra-entrega al proveedor). Cancelamos explícitamente el remanente
            # abierto de la línea. En recepción de 1, 2 o 3 pasos el pendiente vive siempre en el move de
            # primer paso (proveedor->entrada), que cuelga de move_ids; core (_action_cancel) propaga a
            # los downstream si hiciera falta. Acotamos a las recepciones forward genuinas del proveedor:
            # excluimos los reemplazos de devolución con cambio (recepción legítima esperada) y las
            # devoluciones al proveedor abiertas sin validar (origin_returned_move_id), que no son parte
            # del remanente y no deben cancelarse.
            rec._get_remaining_moves_to_cancel().with_context(cancel_from_order=True)._action_cancel()
            if rec.product_qty < old_product_qty:
                rec.order_id._log_decrease_ordered_quantity({rec: (rec.product_qty, old_product_qty)})
            rec.order_id.message_post(
                body=_('Cancel remaining call for line "%s" (id %s), line qty updated from %s to %s')
                % (rec.label, rec.id, old_product_qty, rec.product_qty)
            )

    def _create_or_update_picking(self):
        # Nothing left to receive: unlike 19, core 20 would create a new receipt for the destination
        # moves still open (MTO) when the line quantity drops
        skip = self.filtered(lambda line: line.id in self.env.context.get("cancel_remaining_line_ids", []))
        return super(PurchaseOrderLine, self - skip)._create_or_update_picking()

    def _get_remaining_moves_to_cancel(self):
        """Open moves of the line, without exchange replacements nor moves created by a return."""
        self.ensure_one()
        return self.move_ids.filtered(
            lambda m: m.state not in ("done", "cancel")
            and not m._is_exchange_receipt()
            and not m.origin_returned_move_id
        )

    def _compute_vouchers(self):
        # Cambiamos esta lógica ya que antes teníamos si o si voucher_ids por dependencias y ahora va a depender de que esté instalado stock_voucher
        for rec in self:
            vouchers = []
            for move in rec.move_ids:
                picking = move.picking_id
                if "voucher_ids" in picking._fields:
                    vouchers += picking.voucher_ids.mapped("display_name")
            rec.vouchers = ", ".join(vouchers)

    @api.depends(
        "display_type",
        "order_id.state",
        "qty_received",
        "qty_returned",
        "product_qty",
        "order_id.force_delivered_status",
    )
    def _compute_receipt_status(self):
        precision = self.env["decimal.precision"].precision_get("Product Unit")
        for line in self:
            if line.display_type or line.state not in ("purchase", "done"):
                line.receipt_status = False
                continue
            if line.order_id.force_delivered_status:
                line.receipt_status = line.order_id.force_delivered_status
                continue

            # 'full' antes que 'pending': una línea sin nada pedido (product_qty 0, ej. anulada
            # bajando la cantidad) no tiene nada por recibir
            qty_total = line.qty_received + line.qty_returned
            if float_compare(qty_total, line.product_qty, precision_digits=precision) >= 0:
                line.receipt_status = "full"
            elif float_is_zero(qty_total, precision_digits=precision):
                line.receipt_status = "pending"
            else:
                line.receipt_status = "partial"

    @api.onchange("product_qty")
    def _onchange_product_qty(self):
        if (
            self.state == "purchase"
            and self.product_id.type in ["product", "consu"]
            and self.product_qty < self._origin.product_qty
        ):
            warning_mess = {
                "title": _("Ordered quantity decreased!"),
                "message": (
                    "¡Está reduciendo la cantidad pedida! Recomendamos usar"
                    " el botón para cancelar remanente y"
                    " luego setear la cantidad deseada."
                ),
            }
            self.product_qty = self._origin.product_qty
            return {"warning": warning_mess}
        return {}

    @api.depends("order_id.state", "move_ids.state", "move_ids.to_refund")
    def _compute_qty_returned(self):
        for line in self:
            qty = 0.0
            # Count only real vendor returns of the line product (excludes the subcontract
            # receipt move, and returns of a product that was later replaced on the line).
            for move in line._get_po_line_moves().filtered(
                lambda m: m.state == "done" and m.to_refund and m._is_purchase_return()
            ):
                qty += move.uom_id._compute_quantity(move.product_uom_qty, line.uom_id)
            line.qty_returned = qty

    # Overwrite the origin method to introduce the qty_on_voucher
    def action_add_all_to_invoice(self):
        for rec in self:
            rec.invoice_qty = rec.qty_on_voucher or (rec.qty_to_invoice + rec.invoice_qty)

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        res = super()._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, supplier, po)
        # copy user_id from replenishment to purchase order
        # Solo asignar user_id si NO viene de una venta (no hay 'origins' en context) y NO es odoobot (uid=1)
        if "origins" not in self.env.context and not po.user_id and not self.env.is_superuser():
            po.user_id = self.env.user
        return res

    @api.model
    def _prepare_purchase_order_line_from_procurement(
        self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po
    ):
        res = super()._prepare_purchase_order_line_from_procurement(
            product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po
        )
        # if price was not computed (not seller or seller price = 0.0), then
        # use standar price
        if not res["price_unit"]:
            price_unit = product_id.with_company(company_id).standard_price
            company_currency = company_id.currency_id
            if price_unit and po.currency_id != company_currency:
                price_unit = company_currency._convert(
                    price_unit, po.currency_id, company_id, po.date_order or fields.Date.today()
                )
            line_uom = self.env["uom.uom"].browse(res["uom_id"])
            if price_unit and line_uom and product_id.uom_id != line_uom:
                price_unit = product_id.uom_id._compute_price(price_unit, line_uom)
            res["price_unit"] = price_unit
        return res

    @api.depends()
    def _compute_price_unit_and_date_planned_and_name(self):
        # Esto lo hacemos por un caso raro de cancelacion de remanentes,
        # Odoo cambia el price_unit del move antes de commitear a 0 la qty y hace que cree contraentregas
        all_lines = self
        for line in all_lines:
            if not line.product_qty:
                all_lines -= line
        super(PurchaseOrderLine, all_lines)._compute_price_unit_and_date_planned_and_name()
