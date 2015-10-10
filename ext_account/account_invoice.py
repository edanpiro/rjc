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

from openerp import models, fields, api

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    supplier_invoice_number = fields.Char(string='Supplier Invoice Number', help="The reference of this invoice as provided by the supplier.", readonly=True, states={'draft':[('readonly', False)], 'proforma':[('readonly', False)], 'proforma2':[('readonly', False)], 'open':[('readonly', False)]})
    supplier_billing_date = fields.Date(string='Supplier Billing Date', readonly=True, states={'draft':[('readonly', False)]}, select=True, help="Supplier Billing Date + Supplier Payment terms = Due Date")
    brand_id = fields.Many2one('brand.brand', string='Brand')
    
    # This method overwrite account_invoice.action_date_assign()
    @api.multi
    def action_date_assign(self):
        for inv in self:
            res = inv.onchange_payment_term_date_invoice(inv.payment_term.id, inv.supplier_billing_date or inv.date_invoice)
            if res and res['value']:
                inv.write(res['value'])
        return True
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: