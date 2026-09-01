##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    internal_notes = fields.Html()
    skip_upload = fields.Boolean(related="company_id.skip_upload", string="Skip File Upload", readonly=True)

    force_invoiced_status = fields.Selection(
        [
            ("no", "Nothing to Bill"),
            ("invoiced", "No Bill to Receive"),
        ],
        tracking=True,
        copy=False,
    )

    @api.depends("force_invoiced_status")
    def _get_invoiced(self):
        for order in self:
            if order.state not in ("purchase", "done"):
                order.invoice_status = "no"
                continue

            if order.force_invoiced_status:
                order.invoice_status = order.force_invoiced_status
                continue

            # we also modify and do in this way to be able
            # use in purchase_usability_return_invoicing
            if any(line.invoice_status == "to invoice" for line in order.order_line):
                order.invoice_status = "to invoice"
            elif all(line.invoice_status == "invoiced" for line in order.order_line):
                order.invoice_status = "invoiced"
            else:
                order.invoice_status = "no"

    def button_set_invoiced(self):
        if not self.env.user.has_group("base.group_system"):
            group = self.env.ref("base.group_system").sudo()
            if group.privilege_id:
                raise UserError(
                    _('Only users with "%s / %s" can Set Invoiced manually') % (group.privilege_id.name, group.name)
                )
            else:
                raise UserError(_('Only users with "%s" can Set Invoiced manually') % (group.name))
        # force_invoiced_status is the only value that survives a recompute: both
        # invoice_status and qty_to_invoice are stored computed fields, so stamping
        # them was undone by the next recompute of the order or its lines.
        self.write({"force_invoiced_status": "invoiced"})
        self.message_post(body=_("Manually setted as invoiced"))

    def write(self, vals):
        self.check_force_invoiced_status(vals)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.check_force_invoiced_status(vals)
        return super().create(vals_list)

    @api.model
    def check_force_invoiced_status(self, vals):
        if vals.get("force_invoiced_status") and not self.env.user.has_group("base.group_system"):
            group = self.env.ref("base.group_system").sudo()
            if group.privilege_id:
                raise UserError(
                    _('Only users with "%s / %s" can Set Invoiced manually') % (group.privilege_id.name, group.name)
                )
            else:
                raise UserError(_('Only users with "%s" can Set Invoiced manually') % (group.name))

    def update_prices_with_supplier_cost(self):
        net_price_installed = "net_price" in self.env["product.supplierinfo"]._fields
        for rec in self.order_line.with_company(self.company_id.id).filtered("price_unit"):
            seller = (
                self.env["product.supplierinfo"]
                .sudo()
                .search(
                    [
                        ("partner_id", "=", rec.order_id.partner_id.id),
                        (
                            "currency_id",
                            "=",
                            rec.order_id.partner_id.property_purchase_currency_id.id or self.currency_id.id,
                        ),
                        ("product_tmpl_id", "=", rec.product_id.product_tmpl_id.id),
                        ("company_id", "=", self.company_id.id),
                    ],
                    limit=1,
                )
            )
            if not seller:
                seller = self.env["product.supplierinfo"].create(
                    {
                        "date_start": rec.order_id.date_order and rec.order_id.date_order.date(),
                        "partner_id": rec.order_id.partner_id.id,
                        "currency_id": rec.order_id.partner_id.property_purchase_currency_id.id or self.currency_id.id,
                        "product_tmpl_id": rec.product_id.product_tmpl_id.id,
                        "company_id": self.company_id.id,
                    }
                )
            price_unit = rec.price_unit
            if rec.product_uom_id and seller.product_uom_id != rec.product_uom_id:
                price_unit = rec.product_uom_id._compute_price(price_unit, seller.product_uom_id)
            if net_price_installed:
                seller.net_price = rec.order_id.currency_id._convert(
                    price_unit,
                    seller.currency_id,
                    rec.order_id.company_id,
                    rec.order_id.date_order or fields.Date.today(),
                )
            else:
                seller.price = rec.order_id.currency_id._convert(
                    price_unit,
                    seller.currency_id,
                    rec.order_id.company_id,
                    rec.order_id.date_order or fields.Date.today(),
                )

    def update_prices(self):
        for line in self.order_line:
            line.with_context(update_prices=True)._compute_price_unit_and_date_planned_and_name()

    def _prepare_invoice(self):
        result = super()._prepare_invoice()
        if self.internal_notes:
            result["internal_notes"] = self.internal_notes
        return result

    def _order_line_view_limit(self):
        """Configurable page size for the order_line list; 0 keeps the core default (ticket 121312)."""
        param = self.env["ir.config_parameter"].sudo().get_param("purchase_ux.order_line_view_limit")
        try:
            # clamp to 0..200 (200 = Odoo's native max; higher only renders more rows)
            return min(max(int(param or 0), 0), 200)
        except ValueError:
            return 0

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type="form", **options):
        key = super()._get_view_cache_key(view_id=view_id, view_type=view_type, **options)
        # only the form arch depends on this param, so vary just the form cache key on change
        if view_type == "form":
            key += (self._order_line_view_limit(),)
        return key

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        limit = self._order_line_view_limit()
        if view_type == "form" and limit:
            for node in arch.xpath("//field[@name='order_line']/list"):
                node.set("limit", str(limit))
        return arch, view
