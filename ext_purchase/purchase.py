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
from openerp.exceptions import Warning

class purchase_order(models.Model):
    
    @api.one
    @api.depends('order_line', 'order_line.product_id', 'invoice_method', 'state')
    def _is_picking_and_service(self):
        noprod = self.test_no_product()
        if noprod and self.invoice_method == 'picking' and self.state == 'approved':
            self.write({'invoice_method':'manual'})
            self.is_picking_and_service = True
        else:
            self.is_picking_and_service = False

    _inherit = 'purchase.order'
        # Extend length of field
    is_picking_and_service = fields.Boolean(compute='_is_picking_and_service', string='No Products')
    
    @api.one
    def test_no_product(self):
        for line in self.order_line:
            if line.product_id and (line.product_id.type <> 'service'):
                return False
        return True
    
    @api.one
    def test_product_mixed_type(self):
        is_service = False
        is_non_service = False
        for line in self.order_line:
            if line.product_id and (line.product_id.type <> 'service'):
                is_non_service = True
            elif line.product_id and (line.product_id.type == 'service'):
                is_service = True
                
        if is_service and is_non_service:
            raise Warning(_('Warning!'), _('Services and Products can not be mixed together!'))
        return True
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: