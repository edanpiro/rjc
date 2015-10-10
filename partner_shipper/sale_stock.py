# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

class sale_order(models.Model):
    _inherit = 'sale.order'
    
#     @api.multi    
#     def _create_pickings_and_procurements(self, order, order_lines, picking_id=False):
#         super(sale_order,self)._create_pickings_and_procurements(order, order_lines, picking_id=picking_id)
#         # update picking created by this order with shipping_id
#         picking_obj = self.env['stock.picking']
#         picking_ids = picking_obj.search([('origin','=',order.name)])
#         picking_ids.write({'shipper_id': order.shipper_id.id})
#         return True

    @api.multi
    def action_ship_create(self):
        res = super(sale_order, self).action_ship_create()
        picking_obj = self.env['stock.picking']
        picking_ids = picking_obj.search([('origin', '=', self.name)])
        picking_ids.write({'shipper_id': self.shipper_id.id})
        return res
       
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: