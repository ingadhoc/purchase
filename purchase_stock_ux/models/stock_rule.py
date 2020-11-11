##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, fields


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _prepare_purchase_order_line(
            self, product_id, product_qty, product_uom, company_id, values, po):
        res = super()._prepare_purchase_order_line(
            product_id=product_id, product_qty=product_qty,
            product_uom=product_uom, company_id=company_id, values=values,
            po=po)
        # if price was not computed (not seller or seller price = 0.0), then
        # use standar price
        if not res['price_unit']:
            price_unit = product_id.with_context(
                force_company=company_id.id).standard_price
            company_currency = company_id.currency_id
            if (
                    price_unit and po.currency_id != company_currency):
                price_unit = company_currency._convert(
                    price_unit, po.currency_id, company_id,
                    po.date_order or fields.Date.today())
            if (
                    price_unit and res['product_uom'] and
                    product_id.uom_id.id != res['product_uom']):
                price_unit = product_id.uom_id._compute_price(
                    price_unit, to_uom_id=res['product_uom'])
            res['price_unit'] = price_unit
        return res

    def _update_purchase_order_line(
            self, product_id, product_qty, product_uom, company_id, values, line):
        res = super()._update_purchase_order_line(product_id, product_qty, product_uom, company_id, values, line)

        # if price was not computed (not seller or seller price = 0.0), then
        # use standar price
        if not res['price_unit']:
            price_unit = product_id.with_context(
                force_company=company_id.id).standard_price
            company_currency = company_id.currency_id
            if (price_unit and line.order_id.currency_id != company_currency):
                price_unit = company_currency._convert(
                    price_unit, line.order_id.currency_id,
                    company_id,
                    line.order_id.date_order or fields.Date.today())
            if (
                    price_unit and product_uom and
                    product_id.uom_id != product_uom):
                price_unit = product_id.uom_id._compute_price(
                    price_unit, to_uom_id=product_uom.id)
            res['price_unit'] = price_unit
        return res
