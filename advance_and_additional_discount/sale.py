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

class sale_order(AdditionalDiscountable, models.Model):
    _inherit = 'sale.order'
    _tax_column = 'tax_id'
    _line_column = 'order_line'
    
    @api.one
    @api.depends('invoice_ids')
    def _invoiced_rate(self):
        if self.invoiced:
            self.invoiced_rate = 100.0
        tot = 0.0
        for invoice in self.invoice_ids:
            if invoice.state not in ('cancel'):
            # if invoice.state not in ('draft', 'cancel'):
                # Do not add amount, it this is a deposit/advance
                # tot += not invoice.is_deposit and not invoice.is_advance and invoice.amount_net  # testing: we use amount_net instead of amount_untaxed
                # We change from amount_net back to amount_untaxed again, due to case #2059 (may need to double check)
                tot += not invoice.is_deposit and not invoice.is_advance and invoice.amount_untaxed
        if tot:
            self.invoiced_rate = min(100.0, tot * 100.0 / (self.amount_untaxed or 1.00))  # <-- changed back to untaxed
        else:
            self.invoiced_rate = 0.0
    
    @api.one
    def _num_invoice(self):
        '''Return the amount still to pay regarding all the payment orders'''
        self._cr.execute('SELECT rel.order_id ' \
                'FROM sale_order_invoice_rel AS rel, account_invoice AS inv ' + \
                'WHERE rel.invoice_id = inv.id AND inv.state <> \'cancel\' And rel.order_id in (%s)' % ','.join(str(x) for x in self.ids))
        invs = self._cr.fetchall()
        for inv in invs:
            self.inv_number = inv[0] + 1
    
    @api.one
    @api.depends('order_line.price_subtotal', 'add_disc', 'order_line.tax_id')
    def _amount_all_wrapper(self):
        return self._amount_sale_generic(sale_order)
    
    @api.one
    def _get_amount_retained(self):
        # Account Retention
        prop = self.env['ir.property'].get('property_account_retention_customer', 'res.partner')
#        prop_id = prop and prop.id or False
        account_id = self.env['account.fiscal.position'].map_account(prop)
        if not account_id:
            self.amount_retained = 0.0
        else:
            self._cr.execute("""select sum(l.debit-l.credit) as amount_debit
                            from account_move_line l
                            inner join
                            (select order_id, move_id from account_invoice inv
                            inner join sale_order_invoice_rel rel
                            on inv.id = rel.invoice_id and order_id = %s) inv
                            on inv.move_id = l.move_id
                            where state = 'valid'
                            and account_id = %s
                            group by order_id
                          """, (self.id, account_id.id))
            amount_debit = self._cr.rowcount and self._cr.fetchone()[0] or 0.0
            amount = self.company_id.currency_id.compute(amount_debit, self.pricelist_id.currency_id)
            self.amount_retained = amount

    invoiced_rate = fields.Float(compute='_invoiced_rate', string='Invoiced Ratio')
    # Additional Discount Feature
    add_disc = fields.Float(string='Additional Discount(%)', digits_compute=dp.get_precision('Additional Discount'), readonly=True, states={'draft': [('readonly', False)]})
    add_disc_amt = fields.Float(compute='_amount_all_wrapper', digits_compute=dp.get_precision('Account'), string='Additional Disc Amt',
                                    store=True, help="The additional discount on untaxed amount.")
    amount_untaxed = fields.Float(compute='_amount_all_wrapper', digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
                                      store=True, help="The amount without tax.")
    amount_net = fields.Float(compute='_amount_all_wrapper', digits_compute=dp.get_precision('Account'), string='Net Amount',
                                      store=True, help="The amount after additional discount.")
    amount_tax = fields.Float(compute='_amount_all_wrapper', digits_compute=dp.get_precision('Account'), string='Taxes',
                                  store=True, help="The tax amount.")
    amount_total = fields.Float(compute='_amount_all_wrapper', digits_compute=dp.get_precision('Account'), string='Total',
                                    store=True, help="The total amount.")
    #Advance Feature
    num_invoice = fields.Float(compute='_num_invoice', string='Number invoices created')
    advance_type = fields.Selection(selection=[('advance', 'Advance on 1st Invoice'), ('deposit', 'Deposit on 1st Invoice')], string='Advance Type',
                                      copy=False, help="Deposit: Deducted full amount on the next invoice. Advance: Deducted in percentage on all following invoices.")
    advance_percentage = fields.Float(string='Advance (%)', digits=(16, 6), required=False, copy=False, readonly=True)
    amount_deposit = fields.Float(string='Deposit Amount', readonly=True, digits_compute=dp.get_precision('Account'), copy=False)
    # Retention Feature
    retention_percentage = fields.Float(string='Retention (%)', digits=(16, 6), required=False, readonly=True, copy=False)
    amount_retained = fields.Float(compute='_get_amount_retained', string='Retained Amount', readonly=True, digits_compute=dp.get_precision('Account'))
    # 'amount_retained': fields.float('Retained Amount',readonly=True, digits_compute=dp.get_precision('Account'))

    @api.multi
    def action_invoice_create(self, grouped=False, states=None, date_invoice=False):
        """Add a discount in the invoice after creation, and recompute the total
        """
        # create the invoice
        inv_id = super(sale_order, self).action_invoice_create(grouped=grouped, states=states, date_invoice=date_invoice)
        # modify the invoice
        inv = self.env['account.invoice'].browse(inv_id)
        inv.write({
            'add_disc': self.add_disc or 0.0,
            'name': self.client_order_ref or ''
        })
        inv.button_compute(set_total=False)
        return inv_id
    
    @api.model
    def _prepare_invoice(self, order, lines):
        invoice_line_obj = self.env['account.invoice.line']
        results = invoice_line_obj.read(lines, ['id', 'is_advance', 'is_deposit'])
        for result in results:
            if result['is_advance']:  # If created for advance, remove it.
                lines.remove(result['id'])
            if result['is_deposit']:  # If created for deposit, remove it.
                lines.remove(result['id'])
        res = super(sale_order, self)._prepare_invoice(order=order, lines=lines)
        return res
    
    @api.multi
    def _check_tax(self):
        # For Advance or Deposit case, loop through each lines, check if tax different.
        if self.advance_type in ['advance', 'deposit']:
            i = 0
            tax_ids = []
            for line in self.order_line:
                next_line_tax_id = [x.id for x in line.tax_id]
                if i > 0 and set(tax_ids) != set(next_line_tax_id):
                    raise Warning(
                        _('Advance/Deposit!'),
                        _('You cannot create lines with different taxes!'))
                tax_ids = next_line_tax_id
                i += 1
        return True
    
    @api.multi
    def write(self, vals):
        res = super(sale_order, self).write(vals)
        self._check_tax()
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
