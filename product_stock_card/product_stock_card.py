# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Mentis d.o.o. (<http://www.mentis.si/openerp>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, fields, models, _
from openerp.tools.sql import drop_view_if_exists
import openerp.addons.decimal_precision as dp

class product_stock_card(models.Model):
    _name = 'product.stock.card'
    _description = 'Product Stock Card'
    _auto = False
    _order = 'product_id, date'
    _table = 'product_stock_card'
    
    @api.one
    def _get_stock_tacking(self):
        uom_obj = self.env['product.uom']
        prod_obj = self.env['product.product']
        location = self._context.get('location', False)

        in_qty = 0.00
        out_qty = 0.00
        qty = uom_obj._compute_qty_obj(self.move_uom, self.picking_qty, self.default_uom)
        if location:
            if self.location_id.id == location:
                out_qty = qty
            else:
                in_qty = qty
        else:
            if self.type == 'in':
                in_qty = qty
            else:
                if self.type == 'adjust':
                    if self.location_id.usage == 'inventory':
                        in_qty = qty
                    else:
                        out_qty = qty
                else:
                    if self.type in ('out', 'internal'):
                        out_qty = qty

        d2 = self.date
        c = self._context.copy()
        c.update({'to_date': d2})
        prd = prod_obj.with_context(c).browse(self.product_id.id)
        self.in_qty = in_qty
        self.out_qty = out_qty 
        self.balance = prd.qty_available

    name = fields.Char(string='Document Name', readonly=True, select=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Picking', readonly=True)
    date = fields.Datetime(string='Date', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    invoice_id = fields.Many2one('account.invoice', string='Invoice', readonly=True)
    price_unit = fields.Float(string='Unit Price', digits_compute=dp.get_precision('Product Price'), readonly=True)
    amount = fields.Float(string='Amount', digits_compute=dp.get_precision('Account'), readonly=True)
    location_id = fields.Many2one('stock.location', string='Source Location', readonly=True, select=True)
    location_dest_id = fields.Many2one('stock.location', string='Dest. Location', readonly=True, select=True)
    picking_qty = fields.Float(string='Picking quantity', readonly=True)
    default_uom = fields.Many2one('product.uom', string='Unit of Measure', readonly=True, select=True)
    move_uom = fields.Many2one('product.uom', string='Unit of Move', readonly=True, select=True)
    in_qty = fields.Float(compute='_get_stock_tacking',
                                   string='In',
                                   digits_compute=dp.get_precision('Account'))
    out_qty = fields.Float(compute='_get_stock_tacking',
                                   string='Out',
                                   digits_compute=dp.get_precision('Account'))
    balance = fields.Float(compute='_get_stock_tacking',
                                   string='Balance',
                                   digits_compute=dp.get_precision('Account'))
    type = fields.Char(string='Type', readonly=True)
    
    def init(self, cr):
        drop_view_if_exists(cr, 'product_stock_card')
        cr.execute("""CREATE OR REPLACE VIEW product_stock_card AS
                      (SELECT sm.id AS id,
                              sm.product_id AS product_id,
                              sp.id AS picking_id,
                              sm.date AS date,
                              pa.id AS partner_id,
                              CASE
                                WHEN spt.code = 'incoming'
                                  THEN pai.id
                                WHEN spt.code = 'outgoing'
                                  THEN sai.id
                                ELSE NULL
                              END AS invoice_id,
                              sm.price_unit AS price_unit,
                              sm.product_qty * sm.price_unit AS amount,
                              case WHEN sp.name is null THEN sm.name ELSE sp.name END as name,
                              sm.location_id as location_id,
                              sm.location_dest_id as location_dest_id,
                              CASE WHEN spt.code = 'internal' and
                                  (select usage from stock_location sl WHERE sl.id = sm.location_id) = (select usage from stock_location sl WHERE sl.id = sm.location_dest_id)
                                  THEN 'move'
                                  WHEN spt.code is null THEN 'adjust'
                                  ELSE spt.code
                              END as type,
                              sm.product_qty as picking_qty,
                              pt.uom_id as default_uom,
                              sm.product_uom as move_uom
                         FROM stock_move AS sm
                              LEFT OUTER JOIN res_partner AS pa ON pa.id = sm.partner_id
                              LEFT OUTER JOIN procurement_order AS pro ON pro.id = sm.procurement_id
                              LEFT OUTER JOIN stock_picking AS sp ON sp.id = sm.picking_id
                              LEFT OUTER JOIN stock_picking_type spt on spt.id = sp.picking_type_id 
                              LEFT OUTER JOIN sale_order_line_invoice_rel AS solir ON solir.order_line_id = pro.sale_line_id
                              LEFT OUTER JOIN purchase_order_line_invoice_rel AS polir ON polir.order_line_id = sm.purchase_line_id
                              LEFT OUTER JOIN account_invoice_line AS sail ON sail.id = solir.invoice_id 
                              LEFT OUTER JOIN account_invoice AS sai ON sai.id = sail.invoice_id
                              LEFT OUTER JOIN account_invoice_line AS pail ON pail.id = polir.invoice_id
                              LEFT OUTER JOIN account_invoice AS pai ON pai.id = pail.invoice_id
                              LEFT OUTER JOIN product_product d on (d.id=sm.product_id)
                              LEFT OUTER JOIN product_template pt on (pt.id=d.product_tmpl_id)
                        WHERE sm.state = 'done' and  sm.location_id <> sm.location_dest_id);""")


class product_product(models.Model):
    _inherit = "product.product"

    stock_card_ids = fields.One2many('product.stock.card', 'product_id', string='Stock Card', copy=False)
