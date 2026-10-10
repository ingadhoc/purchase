##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


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

    # NOTA (123822): acá vivía un override de _prepare_merge_moves_distinct_fields que, bajo
    # cancel_from_order, sacaba price_unit de la clave de merge para que al cancelar remanente
    # el move negativo pudiera netear contra el pendiente aunque el costo/descuento hubiera
    # cambiado. Como stock_ux inyecta cancel_from_order=True en TODOS los merges, ese override
    # aflojaba también el merge positivo-positivo de toda confirmación de compra (over-broad).
    # Se reemplazó por el override de _prepare_merge_negative_moves_excluded_distinct_fields en
    # stock_ux, que excluye price_unit SOLO de la clave del move negativo: el neteo de cancelar
    # remanente sigue funcionando y el merge positivo vuelve a ser estricto por price_unit.
