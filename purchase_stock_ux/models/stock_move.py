##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    purchase_id = fields.Many2one(
        related="purchase_line_id.order_id",
    )

    def _compute_origin_description(self):
        super()._compute_origin_description()
        for rec in self:
            if rec.purchase_line_id:
                rec.origin_description = rec.purchase_line_id.name

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        # Esto lo hacemos porque si por ejemplo el replenishment_cost del producto cambió, este cambia el price unit al momento
        # de ver si mergea moves o no, y como siempre queremos que mergee lo sacamos, no es elegante pero resuelve.
        distinct_fields = super()._prepare_merge_moves_distinct_fields()
        if self.env.context.get("cancel_from_order") and "price_unit" in distinct_fields:
            distinct_fields.remove("price_unit")
        return distinct_fields

    def _is_exchange_move_helper(self):
        # Como is_exchange_move se crea en sale_stock_ux, chequeamos si el campo existe antes de usarlo
        # sino existe el valor deberia ser False
        # en 19 vamos mover el campo a stock ux asi no tenemos que hacer este
        # feo hack
        self.ensure_one()
        if self.fields_get().get("is_exchange_move"):
            return self.is_exchange_move
        return False
