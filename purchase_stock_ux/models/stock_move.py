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

    @api.model
    def _prepare_merge_negative_moves_excluded_distinct_fields(self):
        # Al cancelar remanente desde la orden (cancel_from_order) Odoo genera un move
        # negativo que tiene que netear (mergear) contra el move pendiente ya existente.
        # Ese move nuevo se construye "fresco" y puede traer valores distintos a los del
        # move pendiente original en campos que forman parte de la clave de merge:
        #   - price_unit: si cambió el replenishment_cost del producto, o si la línea tiene
        #     descuento (el move pendiente viejo quedó con el precio de lista y el nuevo se
        #     arma con price_unit_discounted).
        #   - location_final_id: el move viejo suele tenerlo vacío y Odoo completa el nuevo
        #     con el default_location_dest_id del tipo de operación (_get_final_location_record).
        # Cualquiera de esas diferencias rompe la clave y, en vez de netear, se genera una
        # contraentrega (OUT). Como en este contexto SIEMPRE queremos que el negativo netee,
        # los excluimos de la clave. Lo hacemos acá (excluded fields del move negativo) y no
        # en _prepare_merge_moves_distinct_fields para que el merge positivo-positivo siga
        # estricto: así no fusionamos por error dos moves vivos del mismo producto que solo
        # difieren en estos campos (ej. cadenas MTO/multi-paso a destinos finales distintos).
        res = super()._prepare_merge_negative_moves_excluded_distinct_fields()
        if self.env.context.get("cancel_from_order"):
            res = res + ["price_unit", "location_final_id"]
        return res
