##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import json
import logging

from lxml import etree
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    delivery_status = fields.Selection(
        [
            ("no", "Not purchased"),
            ("to receive", "To Receive"),
            ("received", "Received"),
        ],
        compute="_compute_delivery_status",
        store=True,
        readonly=True,
        copy=False,
        default="no",
    )
    vouchers = fields.Char(compute="_compute_vouchers")

    qty_on_voucher = fields.Float(
        compute="_compute_qty_on_voucher",
        string="On Voucher",
        digits="Product Unit of Measure",
    )

    qty_returned = fields.Float(
        string="Returned", copy=False, default=0.0, readonly=True, compute="_compute_qty_returned"
    )

    @api.depends_context("voucher")
    def _compute_qty_on_voucher(self):
        # al calcular por voucher no tenemos en cuenta el metodo de facturacion
        # es decir, que calculamos como si fuese metodo segun lo recibido
        voucher = self._context.get("voucher", False)
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
            done_dest_moves = line.move_dest_ids.filtered(lambda m: m.state == "done" and not m.scrapped)
            if done_dest_moves:
                line.move_dest_ids = [fields.Command.unlink(move.id) for move in done_dest_moves]
        return super().unlink()

    def button_cancel_remaining(self):
        # la cancelación de kits no está bien resuelta ya que odoo
        # solo computa la cantidad entregada cuando todo el kit se entregó.
        # Cuestión que, por ahora, desactivamos la cancelación de kits.

        # Manejar órdenes bloqueadas (done): desbloquear temporalmente sin tracking
        orders_to_relock = self.env["purchase.order"]
        for order in self.mapped("order_id").filtered(lambda o: o.state == "done"):
            orders_to_relock |= order
            # Desbloquear sin generar mensaje en el chatter
            order.with_context(tracking_disable=True).write({"state": "purchase"})

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
            # Resetear printed=False en pickings asociados para evitar contra-entregas
            printed_pickings = rec.move_ids.mapped("picking_id").filtered("printed")
            if printed_pickings:
                printed_pickings.write({"printed": False})
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
            rec.move_ids.filtered(
                lambda m: m.state not in ("done", "cancel")
                and not m._is_exchange_move_helper()
                and not m.origin_returned_move_id
            ).with_context(cancel_from_order=True)._action_cancel()
            if rec.product_qty < old_product_qty:
                rec.order_id._log_decrease_ordered_quantity({rec: (rec.product_qty, old_product_qty)})
            rec.order_id.message_post(
                body=_('Cancel remaining call for line "%s" (id %s), line qty updated from %s to %s')
                % (rec.name, rec.id, old_product_qty, rec.product_qty)
            )

        # Volver a bloquear las órdenes que estaban bloqueadas sin generar mensaje
        if orders_to_relock:
            orders_to_relock.with_context(tracking_disable=True).write({"state": "done"})

    def _compute_vouchers(self):
        # Cambiamos esta lógica ya que antes teníamos si o si voucher_ids por dependencias y ahora va a depender de que esté instalado stock_voucher
        for rec in self:
            vouchers = []
            for move in rec.move_ids:
                picking = move.picking_id
                if "voucher_ids" in picking._fields:
                    vouchers += picking.voucher_ids.mapped("display_name")
            rec.vouchers = ", ".join(vouchers)

    @api.depends("order_id.state", "qty_received", "qty_returned", "product_qty", "order_id.force_delivered_status")
    def _compute_delivery_status(self):
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        for line in self:
            if line.state not in ("purchase", "done"):
                line.delivery_status = "no"
                continue
            if line.order_id.force_delivered_status:
                line.delivery_status = line.order_id.force_delivered_status
                continue
            if (
                float_compare((line.qty_received + line.qty_returned), line.product_qty, precision_digits=precision)
                == -1
            ):
                line.delivery_status = "to receive"
            elif (
                float_compare((line.qty_received + line.qty_returned), line.product_qty, precision_digits=precision)
                >= 0
            ):
                line.delivery_status = "received"
            else:
                line.delivery_status = "no"

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

    @api.depends("qty_received_method", "qty_received_manual")
    def _compute_qty_received(self):
        super()._compute_qty_received()
        for line in self.filtered(lambda l: l.qty_received_method in ["manual", "stock_moves"]):
            exchange_move_ids = line.move_ids.filtered(
                lambda m: m.state == "done" and m.location_id.usage != "supplier" and m._is_exchange_move_helper()
            )
            if exchange_move_ids:
                line.qty_received -= sum(
                    line.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                    for move in exchange_move_ids
                )

    @api.depends("order_id.state", "move_ids.state", "move_ids.to_refund")
    def _compute_qty_returned(self):
        for line in self:
            qty = 0.0
            for move in line._get_po_line_moves().filtered(
                lambda m: (
                    m.state == "done"
                    and m.location_id.usage != "supplier"
                    and m.to_refund
                    and not m._is_exchange_move_helper()
                )
            ):
                qty += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
            line.qty_returned = qty

    # Overwrite the origin method to introduce the qty_on_voucher
    def action_add_all_to_invoice(self):
        for rec in self:
            rec.invoice_qty = rec.qty_on_voucher or (rec.qty_to_invoice + rec.invoice_qty)

    @api.model
    def fields_view_get(self, view_id=None, view_type="form", toolbar=False, submenu=False):
        """
        If we came from invoice, we send in context 'force_line_edit'
        and we change list view to make editable and also field qty
        """
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self._context.get("force_line_edit") and view_type == "tree":
            doc = etree.XML(res["arch"])
            placeholder = doc.xpath("//field[1]")[0]
            placeholder.addprevious(
                etree.Element(
                    "field",
                    {
                        "name": "qty_on_voucher",
                    },
                )
            )

            # make all fields not editable
            node = doc.xpath("//field[1]")[0]
            node.set("readonly", "1")
            modifiers = json.loads(node.get("modifiers") or "{}")
            modifiers["readonly"] = True
            node.set("modifiers", json.dumps(modifiers))
            res["fields"].update(self.fields_get(["qty_on_voucher"]))
            res["arch"] = etree.tostring(doc)

        return res

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        res = super()._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, supplier, po)
        # copy user_id from replenishment to purchase order
        # Solo asignar user_id si NO viene de una venta (no hay 'origins' en context) y NO es odoobot (uid=1)
        if "origins" not in self._context and not po.user_id and not self.env.is_superuser():
            po.user_id = self.env.user
        return res

    @api.depends("qty_invoiced", "qty_received", "order_id.state", "qty_returned")
    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        for line in self:
            if line.order_id.state in ["purchase", "done"]:
                if line.product_id.purchase_method == "purchase":
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced - line.qty_returned
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.depends("order_id.state", "qty_invoiced", "product_qty", "qty_to_invoice", "order_id.force_invoiced_status")
    def _compute_invoice_status(self):
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        super()._compute_invoice_status()
        for line in self:
            if line.order_id.force_invoiced_status:
                # keep the forced status that super() already applied
                continue
            if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = "to invoice"
            elif (
                float_compare(line.qty_invoiced, (line.product_qty - line.qty_returned), precision_digits=precision)
                >= 0
            ):
                line.invoice_status = "invoiced"
            else:
                line.invoice_status = "no"

    @api.depends()
    def _compute_price_unit_and_date_planned_and_name(self):
        # Esto lo hacemos por un caso raro de cancelacion de remanentes,
        # Odoo cambia el price_unit del move antes de commitear a 0 la qty y hace que cree contraentregas
        all_lines = self
        for line in all_lines:
            if not line.product_qty:
                all_lines -= line
        super(PurchaseOrderLine, all_lines)._compute_price_unit_and_date_planned_and_name()
