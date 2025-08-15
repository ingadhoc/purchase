##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class StockRule(models.Model):
    _inherit = "stock.rule"

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, po):
        res = super()._prepare_purchase_order_line(
            product_id=product_id,
            product_qty=product_qty,
            product_uom=product_uom,
            company_id=company_id,
            values=values,
            po=po,
        )
        # if price was not computed (not seller or seller price = 0.0), then
        # use standar price
<<<<<<< 3064cbc58fefddca3ef1a0c54af6043e1f6791e7
        if not res["price_unit"]:
            price_unit = product_id.with_context(force_company=company_id.id).standard_price
||||||| 1993b173fff6880e12e9258ce4e3c0354f34e223
        if not res['price_unit']:
            price_unit = product_id.with_context(
                force_company=company_id.id).standard_price
=======
        # Solo asignar user_id si NO es odoobot (uid=1) y la PO no tiene usuario asignado
        if not po.user_id and not self.env.is_superuser():
            po.user_id = self.env.user
        if not res['price_unit']:
            price_unit = product_id.with_context(
                force_company=company_id.id).standard_price
>>>>>>> ec4caf837bbf5610f56ac5fa17d7e0049506ee7d
            company_currency = company_id.currency_id
            if price_unit and po.currency_id != company_currency:
                price_unit = company_currency._convert(
                    price_unit, po.currency_id, company_id, po.date_order or fields.Date.today()
                )
            if price_unit and res["product_uom"] and product_id.uom_id.id != res["product_uom"]:
                product_uom = self.env["uom.uom"].browse(res["product_uom"])
                price_unit = product_id.uom_id._compute_price(price_unit, product_uom)
            res["price_unit"] = price_unit
        return res

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        res = super()._update_purchase_order_line(product_id, product_qty, product_uom, company_id, values, line)

        # if price was not computed (not seller or seller price = 0.0), then
        # use standar price
        if not res["price_unit"]:
            price_unit = product_id.with_context(force_company=company_id.id).standard_price
            company_currency = company_id.currency_id
            if price_unit and line.order_id.currency_id != company_currency:
                price_unit = company_currency._convert(
                    price_unit, line.order_id.currency_id, company_id, line.order_id.date_order or fields.Date.today()
                )
            if price_unit and line.product_uom and product_id.uom_id != line.product_uom:
                price_unit = product_id.uom_id._compute_price(price_unit, line.product_uom)
            res["price_unit"] = price_unit
        return res

    def _make_po_get_domain(self, company_id, values, partner):
        domain = super()._make_po_get_domain(company_id, values, partner)
        current_user_id = self.env.user.id
        new_domain = []
        config = self.env["res.config.settings"].sudo().get_values()
        for condition in domain:
            field, operator, value = condition
<<<<<<< 3064cbc58fefddca3ef1a0c54af6043e1f6791e7
            if field == "user_id" and value == False:
                new_domain.extend(
                    [
                        "|",
                        ("user_id", "=", False),
                        ("user_id", "=", current_user_id),
                    ]
                )
            elif (
                field == "currency_id"
                and config.get("use_supplier_currency", False)
                and partner.property_purchase_currency_id
                and partner.property_purchase_currency_id.id != value
            ):
                value = partner.property_purchase_currency_id.id
                new_domain.append((field, operator, value))
||||||| 1993b173fff6880e12e9258ce4e3c0354f34e223
            if field == 'user_id' and value == False:
                new_domain.extend([
                    '|',
                    ('user_id', '=', False),
                    ('user_id', '=', current_user_id),
                ])
=======
            if field == 'user_id' and value == False:
                # Si viene de una venta (origins en context) o es odoobot, solo buscar POs sin usuario
                if 'origins' in self._context or self.env.is_superuser():
                    new_domain.append(('user_id', '=', False))
                else:
                    # Para otros usuarios, buscar POs sin usuario o del mismo usuario
                    new_domain.extend([
                        ('user_id', '=', current_user_id),
                    ])
>>>>>>> ec4caf837bbf5610f56ac5fa17d7e0049506ee7d
            else:
                new_domain.append(condition)
        return tuple(new_domain)
