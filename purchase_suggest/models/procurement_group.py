from odoo import models


class ProcurementGroup(models.Model):
    _inherit = "procurement.group"

    def _get_orderpoint_domain(self, company_id=False):
        domain = super(ProcurementGroup, self)._get_orderpoint_domain(
            company_id=company_id)
        domain += [('suggest', '=', False)]
        return domain
