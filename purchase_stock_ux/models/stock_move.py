##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    purchase_id = fields.Many2one(
        related="purchase_line_id.order_id",
        string="Purchase Order",
    )

    def _compute_origin_description(self):
        super()._compute_origin_description()
        for rec in self:
            if rec.purchase_line_id:
                rec.origin_description = rec.purchase_line_id.name

    def _is_exchange_receipt(self):
        # Replacement receipt created with "Exchange" on a vendor return (no origin returned move).
        # Core may later add other moves of the line to that picking: those are created afterwards.
        self.ensure_one()
        return bool(
            self.picking_id.return_id
            and not self.origin_returned_move_id
            and self.create_date == self.picking_id.create_date
        )

    def _should_count_for_quantity_received(self):
        # An exchange receipt restocks a vendor return that did not update the PO (returns made in 19)
        if self._is_exchange_receipt() and not self.to_refund:
            return False
        return super()._should_count_for_quantity_received()

    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        order = self.purchase_line_id.order_id
        if len(order) == 1 and order.internal_notes:
            vals["note"] = order.internal_notes
        return vals

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        # Esto lo hacemos porque si por ejemplo el replenishment_cost del producto cambió, este cambia el price unit al momento
        # de ver si mergea moves o no, y como siempre queremos que mergee lo sacamos, no es elegante pero resuelve.
        distinct_fields = super()._prepare_merge_moves_distinct_fields()
        if self.env.context.get("cancel_from_order") and "price_unit" in distinct_fields:
            distinct_fields.remove("price_unit")
        return distinct_fields
