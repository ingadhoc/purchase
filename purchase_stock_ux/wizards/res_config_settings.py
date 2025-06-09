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
        get_param = self.env["ir.config_parameter"].sudo().get_param
        res.update(
            propagate_uom=get_param("stock.propagate_uom", "0") == "1",
            use_supplier_currency=get_param("purchase.use_supplier_currency", "0") == "1",
        )
        return res

    def set_values(self):
        super().set_values()
        set_param = self.env["ir.config_parameter"].sudo().set_param
        set_param("stock.propagate_uom", repr(1 if self.propagate_uom else 0))
        set_param("purchase.use_supplier_currency", repr(1 if self.use_supplier_currency else 0))
