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
import openerp.addons.decimal_precision as dp
from common import AdditionalDiscountable

class purchase_order(AdditionalDiscountable, models.Model):
    _inherit = 'purchase.order'
    _description = 'Purchase Order'

    _tax_column = 'taxes_id'
    _line_column = 'order_line'
    
    @api.one
    @api.depends('invoice_ids')
    def _invoiced_rate(self):
        tot = 0.0
        for invoice in self.invoice_ids:
            if invoice.state not in ('cancel'):
            # if invoice.state not in ('draft', 'cancel'):
                # Do not add amount, it this is a deposit/advance
                # tot += not invoice.is_deposit and not invoice.is_advance and invoice.amount_net  # testing: we use amount_net instead of amount_untaxed
                # We change from amount_net back to amount_untaxed again, due to case #2059 (may need to double check)
                tot += not invoice.is_deposit and not invoice.is_advance and invoice.amount_untaxed  # testing: we use amount_net instead of amount_untaxed
        if self.amount_untaxed:
            self.invoiced_rate = tot * 100.0 / self.amount_untaxed  # <-- changed back to untaxed
        else:
            self.invoiced_rate = 0.0
    
    @api.one
    @api.depends('amount_deposit')
    def _invoiced(self):
        deposit_invoiced = self._deposit_invoiced()
        invoiced = False
        if self.invoiced_rate >= 100.00 and deposit_invoiced:
            invoiced = True
        self.invoiced = invoiced
    
    @api.one
    def _deposit_invoiced(self):
        tot = 0.0
        for invoice in self.invoice_ids:
            if invoice.state not in ('draft', 'cancel'):
                tot += invoice.amount_deposit
        if self.amount_deposit > 0.0:
            if tot >= self.amount_deposit:
                return True
        else:
            return True
    
    @api.one
    def _num_invoice(self):
        '''Return the amount still to pay regarding all the payment orders'''
        res = dict.fromkeys(self.ids, False)

        self._cr.execute('SELECT rel.purchase_id, count(rel.purchase_id) ' \
                'FROM purchase_invoice_rel AS rel, account_invoice AS inv ' + \
                'WHERE rel.invoice_id = inv.id AND inv.state <> \'cancel\' And rel.purchase_id in (%s) group by rel.purchase_id' % ','.join(str(x) for x in self.ids))
        invs = self._cr.fetchall()

        if invs:
            self.num_invoice = invs[0][0]
        return res
    
    @api.one
    @api.depends('order_line', 'add_disc', 'order_line.taxes_id')
    def _amount_all(self):
        return self._amount_all_generic(purchase_order)

    invoiced_rate = fields.Float(compute='_invoiced_rate', string='Invoiced')
    invoiced = fields.Float(compute='_invoiced', string='Invoice Received', help="It indicates that an invoice has been paid")
    add_disc = fields.Float(string='Additional Discount(%)', digits_compute=dp.get_precision('Additional Discount'),
                             states={'confirmed': [('readonly', True)],
                                     'approved': [('readonly', True)],
                                     'done': [('readonly', True)]})
    add_disc_amt = fields.Float(compute='_amount_all', store=True, digits_compute=dp.get_precision('Account'),
                                    string='Additional Disc Amt', help="The additional discount on untaxed amount.")
    amount_net = fields.Float(compute='_amount_all', store=True,
                                  digits_compute=dp.get_precision('Account'), string='Net Amount', help="The amount after additional discount.")
    amount_untaxed = fields.Float(compute='_amount_all', store=True, 
                                      digits_compute=dp.get_precision('Purchase Price'), string='Untaxed Amount', help="The amount without tax")
    amount_tax = fields.Float(compute='_amount_all', store=True,
                                  digits_compute=dp.get_precision('Purchase Price'), string='Taxes', help="The tax amount")
    amount_total = fields.Float(compute='_amount_all', store=True,
                                 digits_compute=dp.get_precision('Purchase Price'), string='Total', help="The total amount")
    # Advance Feature
    num_invoice = fields.Float(compute='num_invoice', string="Number invoices created", store=True)
    advance_type = fields.Selection(selection=[('advance', 'Advance on 1st Invoice'), ('deposit', 'Deposit on 1st Invoice')], string='Advance Type',
                                     copy=False,
                                     help="Deposit: Deducted full amount on the next invoice. Advance: Deducted in percentage on all following invoices.")
    advance_percentage = fields.Float(string='Advance (%)', digits=(16, 6), required=False, readonly=True, copy=False)
    amount_deposit = fields.Float(string='Deposit Amount', readonly=True, digits_compute=dp.get_precision('Account'), copy=False)

    @api.multi
    def action_invoice_create(self):
        """Add a discount in the invoice after creation, and recompute the total
        """
        for order in self:
            # create the invoice
            inv_id = super(purchase_order, self).action_invoice_create()
            # modify the invoice
            inv = self.env['account.invoice'].browse(inv_id)
            inv.write({'add_disc': order.add_disc or 0.0})
            inv.button_compute(set_total=True)
            res = inv_id
        return res
    
    @api.multi
    def _check_tax(self):
        # loop through each lines, check if tax different.
        for order in self:
            if order.advance_type in ['advance', 'deposit']:
                i = 0
                tax_ids = []
                for line in order.order_line:
                    next_line_tax_id = [x.id for x in line.taxes_id]
                    if i > 0 and set(tax_ids) != set(next_line_tax_id):
                        raise Warning(
                            _('Advance/Deposit!'),
                            _('You cannot create lines with different taxes!'))
                    tax_ids = next_line_tax_id
                    i += 1
        return True
    
    @api.multi
    def write(self, vals):
        res = super(purchase_order, self).write(vals)
        self._check_tax()
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: