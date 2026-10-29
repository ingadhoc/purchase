##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    propagate_uom = fields.Boolean(
        "Propagate unit of measure",
    )

    use_supplier_currency = fields.Boolean(
        "Create purchase order in supplier's currency",
    )

    def get_values(self):
        res = super().get_values()
        get_bool = self.env["ir.config_parameter"].sudo().get_bool
        res.update(
            propagate_uom=get_bool("stock.propagate_uom"),
            use_supplier_currency=get_bool("purchase.use_supplier_currency"),
        )
        return res

    def set_values(self):
        super().set_values()
        set_bool = self.env["ir.config_parameter"].sudo().set_bool
        set_bool("stock.propagate_uom", self.propagate_uom)
        set_bool("purchase.use_supplier_currency", self.use_supplier_currency)
