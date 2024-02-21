from odoo import _, api, fields, models
from odoo.exceptions import UserError

class PurchaseRequest(models.Model):

    _inherit = 'purchase.request'

    is_user_id = fields.Boolean(compute='_compute_current_user_id')

    def _compute_current_user_id(self):
        for rec in self:
            if rec.requested_by == self.env.user:
                rec.is_user_id = True
            else:
                rec.is_user_id = False
