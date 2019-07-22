##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    @api.multi
    def _prepare_purchase_order_line(
            self, product_id, product_qty, product_uom, values, po, supplier):
        self.ensure_one()
        res = super(ProcurementRule, self)._prepare_purchase_order_line(
            product_id=product_id, product_qty=product_qty,
            product_uom=product_uom, values=values,
            po=po, supplier=supplier)
        # if price was not computed (not seller or seller price = 0.0), then
        # use standar price
        if not res['price_unit']:
            price_unit = product_id.with_context(
                force_company=values['company_id'].id).standard_price
            company_currency = values['company_id'].currency_id
            if (
                    price_unit and po.currency_id != company_currency):
                price_unit = company_currency.compute(
                    price_unit, po.currency_id)
            if (
                    price_unit and res['product_uom'] and
                    product_id.uom_id.id != res['product_uom']):
                price_unit = product_id.uom_id._compute_price(
                    price_unit, self.env['product.uom'].browse(
                        res['product_uom']))
            res['price_unit'] = price_unit
        return res

    def _update_purchase_order_line(
            self, product_id, product_qty, product_uom, values, line, partner):
        res = super(ProcurementRule, self)._update_purchase_order_line(
            product_id, product_qty, product_uom, values, line, partner)

        # if price was not computed (not seller or seller price = 0.0), then
        # use standar price
        if not res['price_unit']:
            price_unit = product_id.with_context(
                force_company=values['company_id'].id).standard_price
            company_currency = values['company_id'].currency_id
            if (price_unit and line.order_id.currency_id != company_currency):
                price_unit = company_currency.compute(
                    price_unit, line.order_id.currency_id)
            if (
                    price_unit and product_uom and
                    product_id.uom_id != product_uom):
                price_unit = product_id.uom_id._compute_price(
                    price_unit, product_uom)
            res['price_unit'] = price_unit
        return res
