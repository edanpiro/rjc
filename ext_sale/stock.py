# BASED ON REV 8377
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

class stock_move(models.Model):
    _inherit = 'stock.move'
    
    special_info = fields.Text(string='Special Instruction', select=False, readonly=True, states={'draft': [('readonly', False)]})
#    @api.model
#    def _prepare_invoice_line(self, group, picking, move_line, invoice_id, invoice_vals):
#        res = super(stock_picking, self)._prepare_invoice_line(group, picking, move_line, invoice_id, invoice_vals)
#        res.update({
#            'special_info': move_line.special_info,
#            'prodlot_id':move_line.prodlot_id.id
#        })
#        return res
    
    @api.model
    def _get_invoice_line_vals(self, move, partner, inv_type, context=None):
        res = super(stock_move, self)._get_invoice_line_vals(move, partner, inv_type)
        res.update({
            'special_info': move.special_info,
            'prodlot_id': move.restrict_lot_id.id
        })
        return res
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: