##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    skip_upload = fields.Boolean(
        related="company_id.skip_upload",
        readonly=False,
        string="Skip Bill File Upload",
        help="When enabled, bills will be created directly without requiring file upload in purchase orders.",
    )
    purchase_order_line_view_limit = fields.Integer(
        string="Purchase order lines per page",
        config_parameter="purchase_ux.order_line_view_limit",
        help="Lines shown per page on the order. Leave empty to keep the default; "
        "a lower value (e.g. 40) speeds up very long orders.",
    )

    @api.onchange("purchase_order_line_view_limit")
    def _onchange_purchase_order_line_view_limit(self):
        # 200 is Odoo's native max page size for the order line list; a higher value
        # only renders more rows and slows the form, so it is capped there.
        if self.purchase_order_line_view_limit < 0:
            self.purchase_order_line_view_limit = 0
        elif self.purchase_order_line_view_limit > 200:
            self.purchase_order_line_view_limit = 200
