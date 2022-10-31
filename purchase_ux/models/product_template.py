##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    # we create this field and make it stored so we can group by it
    main_seller_id = fields.Many2one(
        string="Main Seller",
        related='seller_ids.partner_id',
        store=True,
    )
