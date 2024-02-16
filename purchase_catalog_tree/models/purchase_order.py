##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, _
from ast import literal_eval


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_add_from_catalog(self):
        action = super().action_add_from_catalog()
        tree_view_id = self.env.ref('purchase_catalog_tree.product_view_tree_catalog').id
        action['views'] = [(tree_view_id, 'tree')] + action['views']
        return action

    def _get_action_add_from_catalog_extra_context(self):
        return {
            **super()._get_action_add_from_catalog_extra_context(),
            'purchase_catalog_tree': True,
        }

    def add_products_to_quotation(self):
        """ In order to filter the products of the partner the "product supplier
        search" module need to be installed
        """
        self.ensure_one()
        action_read = self.env["ir.actions.actions"]._for_xml_id(
            'product.product_normal_action_sell')
        context = literal_eval(action_read['context'])
        if 'search_default_filter_to_sell' in context:
            context.pop('search_default_filter_to_sell')
        context.update(dict(
            search_default_filter_to_purchase=True,
            search_default_seller_ids=self.partner_id.name,
            purchase_catalog_tree=True,
            # we send company in context so it filters taxes
            company_id=self.company_id.id,
            # pricelist=self.pricelist_id.display_name,
            partner_id=self.partner_id.id,
        ))
        # we do this apart because we need to ensure "warehouse_id" exists in datebase, if for the case that
        # we don't have inventory installed yet
        # for this to work stock_ux needs to be installed because it's adding those filters on every view
        if 'picking_type_id' in self._fields:
            context.update(dict(
                search_default_location_id=self.picking_type_id.warehouse_id.lot_stock_id.id,
            ))
        action_read.update(dict(
            context=context,
            name=_('Quotation Products'),
            display_name=_('Quotation Products'),
        ))
        return action_read
    def add_products(self, product, qty):
        """This method create line in cache to prepare the order line that
        it's added to purchase order
        """
        self.ensure_one()
        vals = {
            'order_id': self.id,
            'product_qty': qty,
            'product_id': product.id or False,
            'partner_id': self.partner_id.id,
        }
        self.env['purchase.order.line'].create(vals)
