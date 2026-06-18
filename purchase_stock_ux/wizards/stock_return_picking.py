##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, models
from odoo.exceptions import UserError


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.model
    def default_get(self, fields):
        """Por defecto marcamos las líneas como 'a abonar' (to_refund). En una devolución
        para cambio el usuario debe destildarlo, ya que el cambio no genera reembolso.
        """
        result = super().default_get(fields)
        try:
            for line in result["product_return_moves"]:
                assert line[0] == 0
                line[2]["to_refund"] = True
        except KeyError:
            pass
        return result

    def action_create_exchanges(self):
        if any(self.product_return_moves.mapped("to_refund")):
            raise UserError(_("You cannot create exchanges for return lines marked to refund."))
        return super(StockReturnPicking, self.with_context(is_exchange_move=True)).action_create_exchanges()


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    def _prepare_move_default_values(self, new_picking):
        vals = super()._prepare_move_default_values(new_picking)
        if self.env.context.get("is_exchange_move"):
            vals["is_exchange_move"] = True
        return vals

    def _prepare_picking_default_values_based_on(self, picking):
        vals = super()._prepare_picking_default_values_based_on(picking)
        if self.env.context.get("is_exchange_move"):
            vals["is_exchange_move"] = True
        return vals
