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

class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    _order = 'order_id desc, sequence, id'
    
    sequence = fields.Integer(string='Sequence', help="Gives the sequence order when displaying a list of sales order lines.", default=1000)

class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"
    _order = 'sequence, id'


class mrp_bom(models.Model):
    _inherit = "mrp.bom"
    _order = 'sequence, id'

class stock_move(models.Model):
    _inherit = "stock.move"
    _order = 'id'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: