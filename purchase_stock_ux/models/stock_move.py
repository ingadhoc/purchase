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

<<<<<<< b133985eee4c6add5f187963a0e3da0652524054
||||||| ca324c496bfce977ff1850b8e51966748643aa73
    def _should_count_for_quantity_received(self):
        # An exchange receipt restocks a vendor return that did not update the PO
        if self.picking_id.return_id and not self.origin_returned_move_id and not self.to_refund:
            return False
        return super()._should_count_for_quantity_received()

=======
    def _is_exchange_receipt(self):
        # A receipt created from a vendor return that did not update the PO (exchange)
        self.ensure_one()
        return bool(self.picking_id.return_id and not self.origin_returned_move_id and not self.to_refund)

    def _should_count_for_quantity_received(self):
        # An exchange receipt restocks a vendor return that did not update the PO
        if self._is_exchange_receipt():
            return False
        return super()._should_count_for_quantity_received()

>>>>>>> 4126a63488396206a7e9615b6f981e34dde655f7
    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        # Esto lo hacemos porque si por ejemplo el replenishment_cost del producto cambió, este cambia el price unit al momento
        # de ver si mergea moves o no, y como siempre queremos que mergee lo sacamos, no es elegante pero resuelve.
        distinct_fields = super()._prepare_merge_moves_distinct_fields()
        if self.env.context.get("cancel_from_order") and "price_unit" in distinct_fields:
            distinct_fields.remove("price_unit")
        return distinct_fields
