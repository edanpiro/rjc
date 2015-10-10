
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

from openerp import api, models

class stock_picking(models.Model):
    _inherit = "stock.picking"    
    
    @api.model
    def _get_price_unit_invoice(self, move_line, type):
        if move_line.purchase_line_id:
            # If uos_id = product.uom_id, do not adjust the unit price
            factor = (move_line.product_uos <> move_line.product_id.uom_id) \
                        and move_line.product_id.uos_coeff \
                        or 1.0
            if move_line.purchase_line_id.order_id.invoice_method == 'picking':
                return move_line.price_unit / factor
            else:
                return move_line.purchase_line_id.price_unit / factor
        return super(stock_picking, self)._get_price_unit_invoice(move_line, type)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: