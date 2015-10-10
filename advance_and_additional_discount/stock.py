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

from openerp import api, fields, models, _
from openerp.exceptions import Warning

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    @api.v7    
    def _get_account_analytic_invoice(self, cursor, user, picking, move_line):
        partner_id = picking.partner_id and picking.partner_id.id or False
        rec = self.pool.get('account.analytic.default').account_get(cursor, user, move_line.product_id.id, partner_id, user, time.strftime('%Y-%m-%d'))
        if rec:
            return rec.analytic_id.id

    @api.multi
    def action_invoice_create(self, journal_id=False, group=False, type='out_invoice'):
        """ Adding Additional Discount % from SO/PO into INV when created from DO """

        assert type in ('out_invoice', 'in_invoice', 'in_refund', 'out_refund')
        model = type in ('out_invoice', 'out_refund') and 'sale.order' or 'purchase.order'

        order_id_name = (model == 'sale.order' and 'sale_id' or 'purchase_id')
        order_ids_name = (model == 'sale.order' and 'sale_order_ids' or 'purchase_order_ids')
        # First create Advance/Deposit Invoice
        inv_obj = self.env['account.invoice']
        for picking in self:
#             if picking[order_id_name] and picking[order_id_name].advance_type:
            if model == 'sale.order':
                order_id = self.env['sale.order'].search([('name' ,'=', picking.origin)], limit=1)
            elif model == 'purchase.order':
                order_id = self.env['purchase.order'].search([('name' ,'=', picking.origin)], limit=1)
            if order_id and order_id.advance_type:    
                advance_type = 'is_advance' if order_id.advance_type == 'advance' else 'is_deposit'
                advance_name = 'Advance' if order_id.advance_type == 'advance' else 'Deposit'
                found = inv_obj.search([(order_ids_name, 'in', [order_id.id]), ('state', '!=', 'cancel'), (advance_type, '=', True)])
                if not found:
                    raise Warning(_('Warning!'),
                            _('Unable to create invoice.! First create %s invoice' % advance_name))

        res = super(stock_picking, self).action_invoice_create(journal_id, group, type)
        # Loop through each id (DO), getting its SO/PO's Additional Discount, Write it to Invoice
        for picking in self:
            if not picking.invoice_state == '2binvoiced':
                continue
            add_disc = 0.0
            invoice_id = res[0]
            if model == 'sale.order':
                orders = inv_obj.browse(invoice_id).sale_order_ids
            else:
                orders = inv_obj.browse(invoice_id).purchase_order_ids
            if orders:
                add_disc = orders[0] and orders[0].add_disc or 0.0
                inv_obj.write([invoice_id], {'add_disc': add_disc})
                inv_obj.button_compute([invoice_id])
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
