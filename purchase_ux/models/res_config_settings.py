##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    skip_upload = fields.Boolean(
        related="company_id.skip_upload",
        readonly=False,
        string="Skip Bill File Upload",
        help="When enabled, bills will be created directly without requiring file upload in purchase orders.",
    )
