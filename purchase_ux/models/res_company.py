##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    skip_upload = fields.Boolean(
        string="Skip Bill File Upload",
        help="When enabled, bills will be created directly without requiring file upload in purchase orders.",
        default=True,
    )
