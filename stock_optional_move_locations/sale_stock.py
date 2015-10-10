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

from openerp import models, fields, api, _

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.model    
    def _run_move_create(self, procurement):
        vals = super(sale_order, self)._run_move_create(procurement)
        if procurement.sale_line_id and procurement.sale_line_id.order_id:
            location_id = procurement.sale_line_id.order_id.partner_shipping_id.delivery_source_loc_id.id or \
                            procurement.sale_line_id.order_id.warehouse_id.delivery_source_loc_id.id or \
                            procurement.sale_line_id.order_id.warehouse_id.lot_stock_id.id
            vals['location_id'] = location_id
        return vals
    
#     @api.model
#     def _prepare_order_line_procurement(self, order, line, group_id=False):
#         vals = super(sale_order, self)._prepare_order_line_procurement(order, line, group_id=group_id)
# #         order.partner_id.delivery_source_loc_id.id
#         location_id = order.partner_shipping_id.delivery_source_loc_id.id or \
#                         order.warehouse_id.delivery_source_loc_id.id or \
#                         order.warehouse_id.lot_stock_id.id
#         vals['location_id'] = location_id
#         return vals
    
#     def _prepare_order_line_move(self, order, line, picking_id, date_planned):
#         res = super(sale_order, self)._prepare_order_line_move(order, line, picking_id, date_planned)
#         order.partner_id.delivery_source_loc_id.id
#         location_id = order.partner_shipping_id.delivery_source_loc_id.id or \
#                         order.shop_id.warehouse_id.delivery_source_loc_id.id or \
#                         order.shop_id.warehouse_id.lot_stock_id.id
#         res.update({'location_id': location_id})
#         return res
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: