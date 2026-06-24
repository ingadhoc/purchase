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
    is_exchange_move = fields.Boolean()

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
        # Un movimiento de cambio (devolución para cambio) no debe mergearse con uno que no lo es,
        # para poder descontarlo del cómputo de cantidad recibida.
        distinct_fields.append("is_exchange_move")
        return distinct_fields
