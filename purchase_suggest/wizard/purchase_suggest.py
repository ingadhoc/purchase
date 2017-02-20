# -*- coding: utf-8 -*-
# © 2015-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.tools import float_compare, float_is_zero
from openerp.exceptions import UserError
import logging

logger = logging.getLogger(__name__)


class PurchaseSuggestGenerate(models.TransientModel):
    _name = 'purchase.suggest.generate'
    _description = 'Start to generate the purchase suggestions'

    categ_ids = fields.Many2many(
        'product.category', string='Product Categories')
    seller_ids = fields.Many2many(
        'res.partner', string='Suppliers',
        domain=[('supplier', '=', True)])
    location_id = fields.Many2one(
        'stock.location', string='Stock Location', required=True,
        default=lambda self: self.env.ref('stock.stock_location_stock'))
    # Without this module, when we use orderpoints, if there are no orderpoints
    # for a consu product, Odoo will not suggest to re-order it.
    # But, with this module, Odoo will also suggest to re-order the consu
    # products, which may not be what the user wants
    add_products_without_order_point = fields.Boolean(
        help='Sugerir tambien para productos sin punto de pedido, se va a '
        'utilizar cantidad mínima y máxima 0.0. NO se tienen en cuenta '
        'productos consumibles',
        default=True,
    )

    @api.model
    def _prepare_suggest_line(self, product_id, qty_dict):
        porderline_id = False
        porderlines = self.env['purchase.order.line'].search([
            ('state', 'not in', ('draft', 'cancel')),
            ('product_id', '=', product_id)],
            order='id desc', limit=1)
        # I cannot filter on 'date_order' because it is not a stored field
        porderline_id = porderlines and porderlines[0].id or False
        future_qty = qty_dict['virtual_available'] + qty_dict['draft_po_qty']
        if float_compare(
                qty_dict['max_qty'], qty_dict['min_qty'],
                precision_rounding=qty_dict['product'].uom_id.rounding) == 1:
            # order to go up to qty_max
            qty_to_order = qty_dict['max_qty'] - future_qty
        else:
            # order to go up to qty_min
            qty_to_order = qty_dict['min_qty'] - future_qty

        # agregamos comprar hasta el max
        op = qty_dict['orderpoint']
        if op:
            reste = (
                op.qty_multiple > 0 and qty_to_order % op.qty_multiple or 0.0)
            if float_compare(
                    reste, 0.0,
                    precision_rounding=op.product_uom.rounding) > 0:
                qty_to_order += op.qty_multiple - reste
                qty_to_order = qty_to_order

        product = qty_dict['product']
        sline = {
            'company_id': (
                qty_dict['orderpoint'] and
                qty_dict['orderpoint'].company_id.id or
                self.env.user.company_id.id),
            'product_id': product_id,
            # 'seller_id': qty_dict['product'].main_seller_id.id or False,
            'virtual_available': qty_dict['virtual_available'],
            'qty_available': qty_dict['qty_available'],
            'incoming_qty': qty_dict['incoming_qty'],
            'outgoing_qty': qty_dict['outgoing_qty'],
            'draft_po_qty': qty_dict['draft_po_qty'],
            'orderpoint_id':
            qty_dict['orderpoint'] and qty_dict['orderpoint'].id,
            'location_id': self.location_id.id,
            'min_qty': qty_dict['min_qty'],
            'max_qty': qty_dict['max_qty'],
            'last_po_line_id': porderline_id,
            'qty_to_order': qty_to_order,
            'rotation': product.get_product_rotation(),
            'location_rotation': product.get_product_rotation(
                self.location_id),
            'seller_id': product.main_seller_id.id,
            'currency_id': product.currency_id.id,
            'replenishment_cost': product.replenishment_cost,
        }
        return sline

    @api.model
    def _prepare_product_domain(self):
        product_domain = []
        if self.categ_ids:
            product_domain.append(
                ('categ_id', 'child_of', self.categ_ids.ids))
        if self.seller_ids:
            product_domain.append(
                ('main_seller_id', 'in', self.seller_ids.ids))
        return product_domain

    @api.model
    def generate_products_dict(self):
        ppo = self.env['product.product']
        swoo = self.env['stock.warehouse.orderpoint']
        products = {}
        op_domain = [
            ('suggest', '=', True),
            ('company_id', '=', self.env.user.company_id.id),
            ('location_id', 'child_of', self.location_id.id),
        ]
        if self.categ_ids or self.seller_ids:

            products_subset = ppo.search(self._prepare_product_domain())
            op_domain.append(('product_id', 'in', products_subset.ids))
        ops = swoo.search(op_domain)

        for op in ops:
            if op.product_id.id not in products:
                products[op.product_id.id] = {
                    'min_qty': op.product_min_qty,
                    'max_qty': op.product_max_qty,
                    'draft_po_qty': 0.0,  # This value is set later on
                    'orderpoint': op,
                    'product': op.product_id,
                }
            else:
                raise UserError(
                    _("There are 2 orderpoints (%s and %s) for the same "
                        "product on stock location %s or its "
                        "children.") % (
                        products[op.product_id.id]['orderpoint'].name,
                        op.name,
                        self.location_id.complete_name))

        # agregamos productos sin orderpoint
        # TODO tal vez querramos agregar parametro para setear si solo product
        # o tambien consumibles
        if self.add_products_without_order_point:
            product_ids = products.keys()
            product_domain = self._prepare_product_domain()
            product_domain += [
                ('type', '=', 'product'),
                ('id', 'not in', product_ids)]
            new_products = self.env['product.product'].search(product_domain)
            for product in new_products:
                # We also want the missing product that have min_qty = 0
                # So we remove "if product.z_stock_min > 0"
                products[product.id] = {
                    'min_qty': 0.0,
                    'max_qty': 0.0,
                    'draft_po_qty': 0.0,  # This value is set later on
                    'orderpoint': False,
                    'product': product,
                }
        return products

    @api.multi
    def run(self):
        self.ensure_one()
        pso = self.env['purchase.suggest']
        polo = self.env['purchase.order.line']
        puo = self.env['product.uom']
        p_suggest_lines = []
        products = self.generate_products_dict()
        # key = product_id
        # value = {'virtual_qty': 1.0, 'draft_po_qty': 4.0, 'min_qty': 6.0}
        # WARNING: draft_po_qty is in the UoM of the product
        logger.info('Starting to compute the purchase suggestions')
        logger.info('Min qty computed on %d products', len(products))
        polines = polo.search([
            ('state', '=', 'draft'), ('product_id', 'in', products.keys())])
        for line in polines:
            qty_product_po_uom = puo._compute_qty_obj(
                line.product_uom, line.product_qty, line.product_id.uom_id)
            products[line.product_id.id]['draft_po_qty'] += qty_product_po_uom
        logger.info('Draft PO qty computed on %d products', len(products))
        virtual_qties = self.pool['product.product']._product_available(
            self._cr, self._uid, products.keys(),
            context={'location': self.location_id.id})
        logger.info('Stock levels qty computed on %d products', len(products))
        for product_id, qty_dict in products.iteritems():
            qty_dict['virtual_available'] =\
                virtual_qties[product_id]['virtual_available']
            qty_dict['incoming_qty'] =\
                virtual_qties[product_id]['incoming_qty']
            qty_dict['outgoing_qty'] =\
                virtual_qties[product_id]['outgoing_qty']
            qty_dict['qty_available'] =\
                virtual_qties[product_id]['qty_available']
            logger.debug(
                'Product ID: %d Virtual qty = %s Draft PO qty = %s '
                'Min. qty = %s',
                product_id, qty_dict['virtual_available'],
                qty_dict['draft_po_qty'], qty_dict['min_qty'])
            compare = float_compare(
                qty_dict['virtual_available'] + qty_dict['draft_po_qty'],
                qty_dict['min_qty'],
                precision_rounding=qty_dict['product'].uom_id.rounding)
            if compare < 0:
                vals = self._prepare_suggest_line(product_id, qty_dict)
                if vals:
                    p_suggest_lines.append(vals)
                    logger.debug(
                        'Created a procurement suggestion for product ID %d',
                        product_id)
        p_suggest_lines_sorted = p_suggest_lines
        # no hay necesidad para esto, podemos ordenar por clase
        # p_suggest_lines_sorted = sorted(
        #     p_suggest_lines, key=lambda to_sort: to_sort['seller_id'])
        if p_suggest_lines_sorted:
            p_suggest_ids = []
            for p_suggest_line in p_suggest_lines_sorted:
                p_suggest = pso.create(p_suggest_line)
                p_suggest_ids.append(p_suggest.id)
            action = self.env['ir.actions.act_window'].for_xml_id(
                'purchase_suggest', 'purchase_suggest_action')
            action.update({
                'target': 'current',
                'domain': [('id', 'in', p_suggest_ids)],
            })
            return action
        else:
            raise UserError(_(
                "There are no purchase suggestions to generate."))


class PurchaseSuggest(models.TransientModel):
    _name = 'purchase.suggest'
    _description = 'Purchase Suggestions'
    _rec_name = 'product_id'

    # campos y métodos agregados agregados
    replenishment_cost = fields.Float(
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        readonly=True,
    )
    virtual_available = fields.Float(
        string='Forecasted Quantity',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Forecast quantity in the unit of measure of the product "
        "(computed as Quantity On Hand - Outgoing + Incoming + Draft PO "
        "quantity)"
    )
    rotation = fields.Float(
        readonly=True,
    )
    location_rotation = fields.Float(
        readonly=True,
    )
    order_amount = fields.Monetary(
        string='Order Amount',
        compute='_compute_order_amount',
        store=True,
    )

    @api.multi
    @api.depends('qty_to_order', 'replenishment_cost')
    def _compute_order_amount(self):
        for rec in self:
            rec.order_amount = rec.replenishment_cost * rec.qty_to_order

    @api.multi
    def action_traceability(self):
        self.ensure_one()
        action = self.env.ref('stock.act_product_stock_move_open')
        if action:
            action_read = action.read()[0]
            # nos da error al querer leerlo como dict
            # context = literal_eval(action_read['context'])
            # context['search_default_product_id'] = self.product_id.id
            # context['default_product_id'] = self.product_id.id
            context = {
                'search_default_future': 1,
                'search_default_picking_type': 1,
                'search_default_product_id': self.product_id.id,
                'default_product_id': self.product_id.id}
            action_read['context'] = context
            return action_read

    # campos originales de purchase suggest
    company_id = fields.Many2one(
        'res.company', string='Company', required=True)
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, readonly=True)
    uom_id = fields.Many2one(
        'product.uom', string='UoM', related='product_id.uom_id',
        readonly=True)
    uom_po_id = fields.Many2one(
        'product.uom', string='Purchase UoM', related='product_id.uom_po_id',
        readonly=True)
    seller_id = fields.Many2one(
        'res.partner', string='Main Supplier', readonly=True,
        domain=[('supplier', '=', True)])
    qty_available = fields.Float(
        string='Quantity On Hand', readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
        help="in the unit of measure of the product")
    incoming_qty = fields.Float(
        string='Incoming Quantity', readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
        help="in the unit of measure of the product")
    outgoing_qty = fields.Float(
        string='Outgoing Quantity', readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
        help="in the unit of measure of the product")
    draft_po_qty = fields.Float(
        string='Draft PO Quantity', readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
        help="Draft purchase order quantity in the unit of measure "
        "of the product (NOT in the purchase unit of measure !)")
    last_po_line_id = fields.Many2one(
        'purchase.order.line', string='Last Purchase Order Line',
        readonly=True)
    last_po_date = fields.Datetime(
        related='last_po_line_id.order_id.date_order',
        string='Date of the Last Order', readonly=True)
    last_po_qty = fields.Float(
        related='last_po_line_id.product_qty', readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
        string='Quantity of the Last Order')
    last_po_uom = fields.Many2one(
        related='last_po_line_id.product_uom', readonly=True,
        string='UoM of the Last Order')
    orderpoint_id = fields.Many2one(
        'stock.warehouse.orderpoint', string='Re-ordering Rule',
        readonly=True)
    location_id = fields.Many2one(
        'stock.location', string='Stock Location', readonly=True)
    min_qty = fields.Float(
        string="Min Quantity", readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
        help="in the unit of measure for the product")
    max_qty = fields.Float(
        string="Max Quantity", readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
        help="in the unit of measure for the product")
    qty_to_order = fields.Float(
        string='Quantity to Order',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Quantity to order in the purchase unit of measure for the "
        "product")


class PurchaseSuggestPoCreate(models.TransientModel):
    _name = 'purchase.suggest.po.create'
    _description = 'PurchaseSuggestPoCreate'

    def _location2pickingtype(self, company, location):
        spto = self.env['stock.picking.type']
        pick_type_dom = [
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', company.id)]
        pick_types = spto.search(
            pick_type_dom + [(
                'default_location_dest_id',
                'child_of',
                location.location_id.id)])
        # I use location.parent_id.id to support 2 step-receptions
        # where the stock.location .type is linked to Warehouse > Receipt
        # but location is Warehouse > Stock
        if not pick_types:
            pick_types = spto.search(pick_type_dom)
            if not pick_types:
                raise UserError(_(
                    "Make sure you have at least an incoming picking "
                    "type defined"))
        return pick_types[0]

    def _prepare_purchase_order(self, partner, company, pick_type):
        po_vals = {
            'partner_id': partner.id,
            'company_id': company.id,
            'picking_type_id': pick_type.id,
        }
        return po_vals

    def _prepare_purchase_order_line(
            self, product, qty_to_order, uom, new_po):
        vals = {
            'product_id': product.id,
            'order_id': new_po.id,
            'name': 'BEFORE ONCHANGE',
            'product_uom': uom.id,
            'product_qty': 1.0,  # no need to set a good value before onchange
            'price_unit': 1.0,  # idem
            'date_planned': fields.Date.context_today(self),
        }
        return vals

    def _create_update_purchase_order(
            self, partner, company, po_lines, location):
        polo = self.env['purchase.order.line']
        poo = self.env['purchase.order']
        puo = self.env['product.uom']
        pick_type = self._location2pickingtype(company, location)
        existing_pos = poo.search([
            ('partner_id', '=', partner.id),
            ('company_id', '=', company.id),
            ('state', '=', 'draft'),
            ('picking_type_id', '=', pick_type.id),
        ])
        if existing_pos:
            # update the first existing PO
            existing_po = existing_pos[0]
            for product, qty_to_order, uom in po_lines:
                existing_polines = polo.search([
                    ('product_id', '=', product.id),
                    ('order_id', '=', existing_po.id),
                ])
                if existing_polines:
                    existing_poline = existing_polines[0]
                    existing_poline.product_qty += puo._compute_qty_obj(
                        uom, qty_to_order, existing_poline.product_uom)
                    existing_poline._onchange_quantity()
                else:
                    pol_vals = self._prepare_purchase_order_line(
                        product, qty_to_order, uom, existing_po)
                    new_po_line = polo.create(pol_vals)
                    new_po_line.onchange_product_id()
                    new_po_line.product_qty = qty_to_order
                    new_po_line._onchange_quantity()
            existing_po.message_post(
                _('Purchase order updated from purchase suggestions.'))
            return existing_po
        else:
            # create new PO
            po_vals = self._prepare_purchase_order(partner, company, pick_type)
            new_po = poo.create(po_vals)
            new_po.onchange_partner_id()
            for product, qty_to_order, uom in po_lines:
                pol_vals = self._prepare_purchase_order_line(
                    product, qty_to_order, uom, new_po)
                new_po_line = polo.create(pol_vals)
                new_po_line.onchange_product_id()
                new_po_line.product_qty = qty_to_order
                new_po_line._onchange_quantity()
            return new_po

    @api.multi
    def create_po(self):
        self.ensure_one()
        # group by supplier
        po_to_create = {}
        # key = (seller, company)
        # value = [(product1, qty1, uom1), (product2, qty2, uom2)]
        psuggest_ids = self.env.context.get('active_ids')
        location = False
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for line in self.env['purchase.suggest'].browse(psuggest_ids):
            if not location:
                location = line.location_id
            if float_is_zero(line.qty_to_order, precision_digits=precision):
                continue
            if not line.seller_id:
                raise UserError(_(
                    "No supplier configured for product '%s'.")
                    % line.product_id.name)
            po_to_create.setdefault(
                (line.seller_id, line.company_id), []).append(
                (line.product_id, line.qty_to_order, line.uom_po_id))
        if not po_to_create:
            raise UserError(_('No purchase orders created or updated'))
        po_ids = []
        for (seller, company), po_lines in po_to_create.iteritems():
            assert location, 'No stock location'
            po = self._create_update_purchase_order(
                seller, company, po_lines, location)
            po_ids.append(po.id)

        action = self.env['ir.actions.act_window'].for_xml_id(
            'purchase', 'purchase_rfq')
        action['domain'] = [('id', 'in', po_ids)]
        return action
