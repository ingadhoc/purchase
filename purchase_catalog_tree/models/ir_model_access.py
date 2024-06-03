##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import api, models, exceptions, _
class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'
    @api.model
    def check(self, model, mode='read', raise_exception=True):
        if isinstance(model, models.BaseModel):
            assert model._name == 'ir.model', 'Invalid model object'
            model_name = model.model
        else:
            model_name = model
        # we need to use this flag to know when the operation is from this modules
        if self._context.get('sale_quotation_products') or self._context.get('purchase_catalog_tree') or self.env.is_superuser():
            return True
