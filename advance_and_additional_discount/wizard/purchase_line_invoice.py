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

import ast
from openerp import models, api

class purchase_line_invoice(models.Model):
    _inherit = 'purchase.order.line_invoice'
    
    @api.multi
    def makeInvoices(self):
        purchase_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']
        invoice_obj = self.env['account.invoice']
        res = super(purchase_line_invoice, self).makeInvoices()
        # retrieve invoice_ids from domain, and compute it.
        domain = ast.literal_eval(res.get('domain'))
        invoice_ids = domain[0][2]
        if invoice_ids:
            invoices = invoice_obj.browse(invoice_ids)
        # get purchase order
            if self._context.get('active_model', False) == 'purchase.order':
                purchase = purchase_obj.browse(self._context.get('active_id', False))
                invoices.write({'add_disc': purchase.add_disc or 0.0})
            else:  # try getting it from purchase_line
                purchase_line = purchase_line_obj.browse(self._context.get('active_ids')[0])
                invoices.write({'add_disc': purchase_line.order_id.add_disc or 0.0})
            invoices.button_compute()
            invoices.button_reset_taxes()
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: