##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    purchase_skip_bill_file_upload = fields.Boolean(
        string="Skip Bill File Upload",
        config_parameter="purchase_ux.skip_bill_file_upload",
        help="When enabled, bills will be created directly without requiring file upload.",
    )
