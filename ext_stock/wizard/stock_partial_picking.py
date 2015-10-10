# -*- coding: utf-8 -*-

#################################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp

class stock_transfer_details_items(models.TransientModel):
    _inherit = 'stock.transfer_details_items'
    
    init_qty = fields.Float(string='Init Qty', digits_compute=dp.get_precision('Product Unit of Measure'), required=True)
    
    @api.multi
    def onchange_quantity(self, quantity, init_qty):
        if not quantity or not init_qty:
            return {'value':{}}
        if quantity > init_qty:
            warning = {
                'title': _('Quantity Warning!'),
                'message' : _('Delivery Quantity more than Initial Quantity is not allowed!')
                }
            value = {'quantity': init_qty}
            return {'warning': warning, 'value': value}
        else:
            return {'value':{}}
    
        return {'value':{}}
        
class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'
    
    date_done = fields.Date(string='Date of Reception')
    
    @api.model    
    def default_get(self, fields):
        res = super(stock_transfer_details, self).default_get(fields)
        picking_ids = self._context.get('active_ids', [])
        active_model = self._context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.env['stock.picking'].browse(picking_id)
        items = []
        packs = []
        if not picking.pack_operation_ids:
            picking.do_prepare_partial()
        for op in picking.pack_operation_ids:
            item = {
                'packop_id': op.id,
                'product_id': op.product_id.id,
                'product_uom_id': op.product_uom_id.id,
                'quantity': op.product_qty,
                'init_qty': op.product_qty,
                'package_id': op.package_id.id,
                'lot_id': op.lot_id.id,
                'sourceloc_id': op.location_id.id,
                'destinationloc_id': op.location_dest_id.id,
                'result_package_id': op.result_package_id.id,
                'date': op.date, 
                'owner_id': op.owner_id.id,
            }
            if op.product_id:
                items.append(item)
            elif op.package_id:
                packs.append(item)
        res.update(item_ids=items)
        res.update(packop_ids=packs)
        return res
    
    @api.one
    def do_detailed_transfer(self):
        super(stock_transfer_details, self).do_detailed_transfer()
        if self.date_done:
            self.picking_id.write({'date_done': self.date_done})
    
#     def _partial_move_for(self, cr, uid, move):
#         partial_move = super(stock_transfer_details, self)._partial_move_for(cr, uid, move)
#         partial_move.update({
#             'init_qty': move.product_qty if move.state in ('assigned', 'draft', 'confirmed') else 0
#         })
#         return partial_move  
    
#     def do_partial(self, cr, uid, ids, context=None):
#         res = super(stock_transfer_details, self).do_partial(cr, uid, ids, context=context)
#         # Update date_done back to picking document
#         stock_picking = self.pool.get('stock.picking')
#         partial = self.browse(cr, uid, ids[0], context=context)
#         if partial.date_done:
#             stock_picking.write(cr, uid, [partial.picking_id.id], {'date_done': partial.date_done})
#         return res
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: