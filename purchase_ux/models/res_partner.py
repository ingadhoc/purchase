##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def get_import_templates(self):
        if self.env.context.get("res_partner_search_mode") == "supplier":
            return [
                {
                    "label": _("Import Template for Vendors"),
                    "template": "/purchase_ux/static/xls/res_partner.xlsx",
                }
            ]
        return super().get_import_templates()
