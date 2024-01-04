##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.tools import float_compare, float_is_zero
from lxml import etree
import json


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    invoice_status = fields.Selection([
        ('no', 'Nothing to Bill'),
        ('to invoice', 'Waiting Invoices'),
        ('invoiced', 'No Bill to Receive'),
    ],
        string='Invoice Status',
        compute='_compute_invoice_status',
        store=True,
        readonly=True,
        copy=False,
        default='no'
    )

    invoice_qty = fields.Float(
        string='Invoice Quantity',
        compute='_compute_invoice_qty',
        inverse='_inverse_invoice_qty',
        search='_search_invoice_qty',
        digits='Product Unit of Measure',
    )

    qty_to_invoice = fields.Float(
        compute='_compute_qty_to_invoice',
        string='Cantidad en factura actual',
        store=True,
        readonly=True,
        digits='Product Unit of Measure',
        default=0.0
    )

    @api.depends(
        'order_id.state', 'qty_invoiced', 'product_qty', 'qty_to_invoice',
        'order_id.force_invoiced_status')
    def _compute_invoice_status(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for line in self:
            if line.state not in ('purchase', 'done'):
                line.invoice_status = 'no'
            elif line.order_id.force_invoiced_status:
                line.invoice_status = line.order_id.force_invoiced_status
            elif not float_is_zero(
                    line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif float_compare(line.qty_invoiced, line.product_qty,
                               precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'

    @api.depends(
        'qty_invoiced', 'qty_received', 'order_id.state')
    def _compute_qty_to_invoice(self):
        for line in self:
            if line.order_id.state in ['purchase', 'done']:
                if line.product_id.purchase_method == 'purchase':
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """
        If we came from invoice, we send in context 'force_line_edit'
        and we change tree view to make editable and also field qty
        """
        res = super().get_view(
            view_id=view_id, view_type=view_type, **options)
        force_line_edit = self._context.get('force_line_edit')
        if force_line_edit and view_type == 'tree':
            doc = etree.XML(res['arch'])
            # add to invoice qty field (before setupmodifis because if not
            # it remains editable)
            placeholder = doc.xpath("//field[1]")[0]
            placeholder.addprevious(
                etree.Element('field', {
                    'name': 'qty_to_invoice',
                    'readonly': '1',
                }))

            # make all fields not editable
            for node in doc.xpath("//field"):
                node.set('readonly', '1')
                modifiers = json.loads(node.get("modifiers") or "{}")
                modifiers['readonly'] = True
                node.set("modifiers", json.dumps(modifiers))

            # add qty field
            placeholder.addprevious(
                etree.Element('field', {
                    'name': 'invoice_qty',
                    # we force editable no matter user rights
                    'readonly': '0',
                }))

            # add button to add all
            placeholder.addprevious(
                etree.Element('button', {
                    'name': 'action_add_all_to_invoice',
                    'type': 'object',
                    'icon': 'fa-plus-square',
                    'help': _('Agregar las cantidades en "Para Facturar" a la factura actual'),
                }))

            # add button tu open form
            placeholder = doc.xpath("//tree")[0]
            placeholder.append(
                etree.Element('button', {
                    'name': 'action_line_form',
                    'type': 'object',
                    'icon': 'fa-external-link',
                    'help': _('Open Purchase Line Form View'),
                }))

            # make tree view editable
            for node in doc.xpath("/tree"):
                node.set('edit', 'true')
                node.set('create', 'false')
                node.set('editable', 'top')
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def action_line_form(self):
        self.ensure_one()
        return {
            'name': _('Purchase Line'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'purchase.order.line',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
        }

    @api.depends_context('active_id')
    def _compute_invoice_qty(self):
        invoice_id = self._context.get('active_id', False)
        if not invoice_id:
            return True
        AccountInvoice = self.env['account.move']
        AccountInvoiceLine = self.env['account.move.line']
        for rec in self:
            lines = AccountInvoiceLine.search([
                ('move_id', '=', invoice_id),
                ('purchase_line_id', '=', rec.id)])
            invoice_qty = -1.0 * sum(
                lines.mapped('quantity')) if AccountInvoice.browse(
                invoice_id).move_type == 'in_refund' else sum(
                    lines.mapped('quantity'))
            rec.invoice_qty = invoice_qty

    def _inverse_invoice_qty(self):
        invoice_id = self._context.get('active_id', False)
        active_model = self._context.get('active_model', False)
        if not invoice_id or active_model != 'account.move':
            return True
        invoice = self.env['account.move'].browse(invoice_id)
        sign = invoice.move_type == 'in_refund' and -1.0 or 1.0
        purchase_lines = self.env['account.move.line'].with_context(
            check_move_validity=False)
        do_not_compute = self._context.get('do_not_compute')
        for rec in self:
            lines = purchase_lines.search([
                ('move_id', '=', invoice_id),
                ('purchase_line_id', '=', rec.id)])
            # TODO ver como agregamos esta validacion de otra manera
            # no funciona bien si, por ej, agregamos una cantidad y luego
            # la aumentamos, en realidad tal vez no hace falta esta validacion
            # y se controla quedando enc antidades negativas. se podria
            # controlar directamente desde el qty_to_invoice con contraint
            # si se necesta
            # if rec.invoice_qty > rec.qty_to_invoice:
            #     raise UserError(_(
            #         'No puede facturar más de lo pendiente a facturar. '
            #         'Verifique la configuración de facturación de sus '
            #         'productos y/o la receipción de la mercadería.'))
            if lines:
                # if there are lines and the amount is zero, we delete
                if not rec.invoice_qty:
                    lines.unlink()
                else:
                    (lines - lines[0]).unlink()
                    lines[0].quantity = sign * rec.invoice_qty
            else:
                # If there are no lines and there is no quantity, then we
                # do not do nothing
                if not rec.invoice_qty:
                    continue
                data = rec._prepare_account_move_line(invoice)
                data['quantity'] = sign * rec.invoice_qty
                data['move_id'] = invoice_id
                invoice_lines = purchase_lines.create(data)
                invoice_lines._compute_tax_ids()
                invoice = invoice_lines.mapped('move_id')
            if do_not_compute:
                continue
            rec._compute_qty_invoiced()

    @api.model
    def _search_invoice_qty(self, operator, operand):
        """
        we just implemented the case "('invoice_qty', '! =', False)" which
        is the one we use in the view and only one that interests us for now
        """
        invoice_id = self._context.get('active_id', False)
        active_model = self._context.get('active_model', False)
        if active_model != 'account.move':
            return []
        return [('invoice_lines.move_id', 'in', [invoice_id])]

    def action_add_all_to_invoice(self):
        for rec in self:
            rec.invoice_qty = (rec.qty_to_invoice + rec.invoice_qty)

    @api.onchange('product_qty', 'product_uom')
    def _compute_price_unit_and_date_planned_and_name(self):
        res = super()._compute_price_unit_and_date_planned_and_name()

        for line in self:
            if not line.product_id:
                continue

            # if price was not computed (not seller or seller price = 0.0), then
            # use standar price
            if not line.price_unit:
                price_unit = line.with_company(line.company_id.id).product_id.standard_price
                if (price_unit and line.currency_id != line.company_id.currency_id):
                    price_unit = line.company_id.currency_id._convert(
                        price_unit, line.currency_id,
                        line.company_id,
                        line.date_order or fields.Date.today())
                if (price_unit and line.product_uom and line.product_id.uom_id != line.product_uom):
                    price_unit = line.product_id.uom_id._compute_price(price_unit, line.product_uom)
                line.price_unit = price_unit
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(PurchaseOrderLine, self).create(vals_list)
        lines._compute_price_unit_and_date_planned_and_name()
        return lines
