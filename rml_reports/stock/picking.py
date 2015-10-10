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

import time
from openerp.report import report_sxw

class picking(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(picking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_product_desc':self.get_product_desc,
            'display_invoice_address':self.display_invoice_address,
            'display_shipper_address':self.display_shipper_address,
            'get_state_value':self.get_state_value
        })
        
    def get_state_value(self, state):
        
        res = {'draft': 'Draft',
               'cancel': 'Cancelled',
               'auto': 'Waiting Another Operation',
               'confirmed': 'Waiting Availability',
               'assigned': 'Ready to Deliver',
               'done': 'Delivered'}
        
        return res[state]
    
    def get_product_desc(self, move_line):
        desc = move_line.name
        if move_line.product_id.default_code:
            desc = '[' + move_line.product_id.default_code + ']' + ' ' + desc
        return desc
    
    def display_invoice_address(self, picking):
        
        # Only for this report, update printed = True
        self.pool.get('stock.picking').write(self.cr, self.uid, picking.id, {'printed':True})
        
        # Get the SO
        order_obj = self.pool.get('sale.order')
        order_ids = order_obj.search(self.cr, self.uid, [('name', '=', picking.origin)], limit=1)
        if len(order_ids) == 0:  # Sale Order not found.
            return False
        order = order_obj.browse(self.cr, self.uid, order_ids[0])
        
        # Get Invoice Address object
        if not (order.partner_invoice_id and order.partner_invoice_id.id):
            return False
                
        address_string = (order.partner_invoice_id.title.name or '') + ' ' + order.partner_invoice_id.name + '\n'
        address_string += self.pool.get('res.partner')._display_address(self.cr, self.uid, order.partner_invoice_id) + '\n'
        address_string += order.partner_invoice_id.phone or order.partner_invoice_id.email or ''
                                            
        return address_string  
    
    def display_shipper_address(self, picking):
                        
        address_string = picking.shipper_id.name + '\n'
        address_string += self.pool.get('partner.shipper')._display_address(self.cr, self.uid, picking.shipper_id) + '\n'
        address_string += picking.shipper_id.phone or picking.shipper_id.email or ''
                                            
        return address_string
    
report_sxw.report_sxw('report.stock.picking.list.rjc', 'stock.picking', '', parser=picking, header="internal")
# report_sxw.report_sxw('report.stock.picking.list.int.rjc', 'stock.picking', '', parser=picking, header="internal")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: