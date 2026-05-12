##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # we create this field and make it stored so we can group by it
    main_seller_id = fields.Many2one(
        string="Main Seller",
        related="seller_ids.partner_id",
        store=True,
    )

    @api.model
    def get_import_templates(self):
        res = super().get_import_templates()
        if self.env.context.get("purchase_product_template"):
            return [
                {
                    "label": _("Import Template for Products"),
                    "template": "/purchase_ux/static/xls/product_template.xlsx",
                }
            ]
        return res
