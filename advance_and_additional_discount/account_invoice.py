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
import openerp.addons.decimal_precision as dp
from openerp import api, fields, models, _
from openerp.exceptions import Warning
from common import AdditionalDiscountable

class account_invoice(AdditionalDiscountable, models.Model):
    _inherit = 'account.invoice'
    _description = 'Invoice'
    _line_column = 'invoice_line'
    _tax_column = 'invoice_line_tax_id'
    
    @api.model
    def record_currency(self, record):
        """Return currency browse record from an invoice record (override)."""
        return record.currency_id
    
    @api.multi
    @api.depends('invoice_line', 'tax_line', 'add_disc')
    def _amount_all(self):
        self._amount_invoice_generic(account_invoice)
    
    amount_untaxed = fields.Float(compute='_amount_all', digits_compute=dp.get_precision('Account'), string='Untaxed', store=True, multi='all')
    add_disc = fields.Float('Additional Discount(%)', digits_compute=dp.get_precision('Additional Discount'), readonly=True, states={'draft': [('readonly', False)]}, default=0.0)
    add_disc_amt = fields.Float(compute='_amount_all', method=True, digits_compute=dp.get_precision('Account'), string='Additional Disc Amt',
                                store=True, multi='all', help="The additional discount on untaxed amount.")
    amount_net = fields.Float(compute='_amount_all', method=True, digits_compute=dp.get_precision('Account'), string='Net Amount',
                              store=True, multi='all', help="The amount after additional discount.")
    # Advance
    is_advance = fields.Boolean(string='Advance', default=False)
    amount_advance = fields.Float(compute='_amount_all', method=True, digits_compute=dp.get_precision('Account'), string='Advance Amt',
                                  store=True, multi='all', help="The advance amount to be deducted according to original percentage")
    # Deposit
    is_deposit = fields.Boolean(string='Deposit', default=False)
    amount_deposit = fields.Float(compute='_amount_all', method=True, digits_compute=dp.get_precision('Account'), string='Deposit Amt',
                                  store=True, multi='all', help="The deposit amount to be deducted in the second invoice according to original deposit")

    amount_beforetax = fields.Float(compute='_amount_all', method=True, digits_compute=dp.get_precision('Account'), string='Before Taxes',
                                    store=True, multi='all', help="Net amount after advance amount deduction")
    # --
    amount_tax = fields.Float(compute='_amount_all', digits_compute=dp.get_precision('Account'), string='Tax', store=True, multi='all')
    # Retention
    is_retention = fields.Boolean(string='Retention', default=False)
    amount_retention = fields.Float(compute='_amount_all', method=True, digits_compute=dp.get_precision('Account'), string='Retention Amt',
                        store=True, help="The amount to be retained according to retention percentage")
    
    amount_beforeretention = fields.Float(compute='_amount_all', digits_compute=dp.get_precision('Account'), string='Before Retention',
                        store=True, help="Net amount after retention deduction")

    amount_total = fields.Float(compute='_amount_all', digits_compute=dp.get_precision('Account'), string='Total', store=True)


    # For refund case, we also copy the Additional Discount. The rest are not copied yet.
    # To copy, we will need to set the relation between refund with SO. This is yet to decide.
    @api.multi
    def _prepare_refund(self, invoice, date=None, period_id=None, description=None, journal_id=None):
        invoice_data = super(account_invoice, self)._prepare_refund(invoice, date=date, period_id=period_id, description=description, journal_id=journal_id)
        invoice_data.update({
            'add_disc': invoice.add_disc
        })
        return invoice_data
    
    @api.model
    def _reset_delivery_2binvoiced(self, module_name):
        picking_pool = self.env['stock.picking']
        picking_ids = picking_pool.search([('invoice_ids', 'in', self.ids)])
       # order_id_name = (module_name == 'sale.order' and 'sale_id' or False)
      #  order_policy = (module_name == 'sale.order' and 'order_policy' or 'invoice_method')
        
        for picking in picking_ids:
            if module_name == 'sale.order':
                if picking['sale_id']['order_policy'] == 'picking':
                    picking.write({'invoice_state': '2binvoiced'})
        return True
    
    @api.model    
    def _reset_advance_type(self, module_name):
        sale_obj = self.env[module_name]

        sale_ids = sale_obj.search([('invoice_ids', 'in', self.ids)])
        res = sale_obj._num_invoice(sale_ids, 'num_invoice', None)
        res = dict((key, value) for key, value in res.iteritems() if value > 1)

        if res:
            res = sale_ids.read(['name'])
            raise Warning(_('Advance/Deposit!'), _('Unable to cancel this invoice.!\n First cancel all Invoice related to %s' % ','.join(x['name'] for x in res)))

        inv_ids = self.search([('id', 'in', self._ids), ('is_deposit', '=', True)])
        if inv_ids:
            sale_ids = sale_obj.search([('invoice_ids', 'in', inv_ids)])
            if sale_ids:
                sale_ids.write({'amount_deposit': False})

        inv_ids = self.search([('id', 'in', self.ids), ('is_advance', '=', True)])
        if inv_ids:
            sale_ids = sale_obj.search([('invoice_ids', 'in', inv_ids)])
            if sale_ids:
                sale_ids.write({'advance_amount': False})
    
    @api.multi
    def action_cancel(self):
        # Purchase
        inv_ids = self.search([('type', '=', 'in_invoice'), ('id', 'in', self.ids), '|', ('is_deposit', '=', True), \
                                         ('is_advance', '=', True)])
        if inv_ids:
            self._reset_advance_type('purchase.order')

        # Sale Order
        inv_ids = self.search([('type', '=', 'out_invoice'), ('id', 'in', self.ids), '|', ('is_deposit', '=', True), \
                                        ('is_advance', '=', True)])
        if inv_ids:
            self._reset_advance_type('sale.order')

        # Reset invoice_state in delivery order is 2binvoiced
        self._reset_delivery_2binvoiced('sale.order')
        self._reset_delivery_2binvoiced('purchase.order')
        super(account_invoice, self).action_cancel()
        return True

    # For Advance/Deposit/Retension case, calc gain/loss on exchange.
    @api.multi
    def compute_invoice_totals(self, company_currency, ref, invoice_move_lines):
        total, total_currency, invoice_move_lines = super(account_invoice, self).compute_invoice_totals(company_currency, ref, invoice_move_lines)
        # If move_line contain advance, recalculate based on the 1st invoice (not cancel)
        invoice_obj = self.env['account.invoice']
        cur_obj = self.env['res.currency']
        new_invoice_move_lines = []
        for i in invoice_move_lines:
            if i['name'] in (_('Advance Amount'), _('Deposit Amount'), _('Retention Amount')):
                if self.sale_order_ids:
                    sale = self.sale_order_ids[0]
                    invoice_ids = [x.id for x in sale.invoice_ids]
                    invoice_ids.sort()
                    for invoice in invoice_obj.browse(invoice_ids):
                        if invoice.state not in ('draft', 'cancel'):
                            #date = invoice.date_invoice
                            #invoice.update({'date': date or time.strftime('%Y-%m-%d')})
                            #new_price = cur_obj.compute(self.currency_id.id,
                             #       company_currency, i['amount_currency'])
                            ctx = {'date':invoice.date_invoice or time.strftime('%Y-%m-%d')}
                            new_price = self.currency_id.with_context(ctx).compute(i['amount_currency'],company_currency)    
                            if i['price'] * new_price < 0:  # Change sign
                                new_price = -new_price
                            amount_gainloss = i['price'] - new_price
                            gain_account_id = self.company_id.income_currency_exchange_account_id.id
                            loss_account_id = self.company_id.expense_currency_exchange_account_id.id
                            account_id = amount_gainloss > 0 and loss_account_id or gain_account_id
                            i['price'] = new_price
                            # Add the gain/loss line
                            i2 = i.copy()
                            i2['account_id'] = account_id
                            i2['price'] = amount_gainloss
                            i2['price_unit'] = abs(amount_gainloss)
                            i2['name'] = _('Gain/Loss Exchange Rate')
                            i2['amount_currency'] = False
                            i2['currency_id'] = False
                            new_invoice_move_lines.append(i2)
                            break
                new_invoice_move_lines.append(i)
            else:
                new_invoice_move_lines.append(i)  
            
        return total, total_currency, new_invoice_move_lines
            
class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    is_advance = fields.Boolean(string='Advance', default=False)
    is_deposit = fields.Boolean(string='Deposit', default=False)

    # testing: also dr/cr advance, force creating new move_line
    @api.model
    def move_line_get(self, invoice_id):
        res = super(account_invoice_line, self).move_line_get(invoice_id)
        inv = self.env['account.invoice'].browse(invoice_id)

        if inv.add_disc_amt > 0.0:
            sign = -1
            # sign = inv.type in ('out_invoice','in_invoice') and -1 or 1
            # account code for advance
            prop = inv.type in ('out_invoice', 'out_refund') \
                        and self.env['ir.property'].get('property_account_add_disc_customer', 'res.partner') \
                        or self.env['ir.property'].get('property_account_add_disc_supplier', 'res.partner')
            #prop_id = prop and prop.id or False
            account_id = self.env['account.fiscal.position'].map_account(prop)            
            res.append({
                'type': 'src',
                'name': _('Additional Discount'),
                'price_unit': sign * inv.add_disc_amt,
                'quantity': 1,
                'price': sign * inv.add_disc_amt,
                'account_id': account_id.id,
                'product_id': False,
                'uos_id': False,
                'account_analytic_id': False,
                'taxes': False,
            })

        if inv.amount_advance > 0.0:
            sign = -1
            # sign = inv.type in ('out_invoice','in_invoice') and -1 or 1
            # account code for advance
            prop = inv.type in ('out_invoice', 'out_refund') \
                        and self.env['ir.property'].get('property_account_advance_customer', 'res.partner') \
                        or self.env['ir.property'].get('property_account_advance_supplier', 'res.partner')
           # prop_id = prop and prop.id or False
            account_id = self.env['account.fiscal.position'].map_account(prop)
            res.append({
                'type': 'src',
                'name': _('Advance Amount'),
                'price_unit': sign * inv.amount_advance,
                'quantity': 1,
                'price': sign * inv.amount_advance,
                'account_id': account_id.id,
                'product_id': False,
                'uos_id': False,
                'account_analytic_id': False,
                'taxes': False,
            })

        if inv.amount_deposit > 0.0:
            sign = -1
            # sign = inv.type in ('out_invoice','in_invoice') and -1 or 1
            # account code for advance
            prop = inv.type in ('out_invoice', 'out_refund') \
                        and self.env['ir.property'].get('property_account_deposit_customer', 'res.partner') \
                        or self.env['ir.property'].get('property_account_deposit_supplier', 'res.partner')

           # prop_id = prop and prop.id or False
            account_id = self.env['account.fiscal.position'].map_account(prop)

            res.append({
                'type': 'src',
                'name': _('Deposit Amount'),
                'price_unit': sign * inv.amount_deposit,
                'quantity': 1,
                'price': sign * inv.amount_deposit,
                'account_id': account_id.id,
                'product_id': False,
                'uos_id': False,
                'account_analytic_id': False,
                'taxes': False,
            })

        if inv.amount_retention > 0.0:
            sign = -1
            # sign = inv.type in ('out_invoice','in_invoice') and -1 or 1
            # account code for advance
            prop = inv.type in ('out_invoice', 'out_refund') \
                        and self.env['ir.property'].get('property_account_retention_customer', 'res.partner') \
                        or self.env['ir.property'].get('property_account_retention_supplier', 'res.partner')
            #prop_id = prop and prop.id or False
            account_id = self.env['account.fiscal.position'].map_account(prop)

            res.append({
                'type': 'src',
                'name': _('Retention Amount'),
                'price_unit': sign * inv.amount_retention,
                'quantity': 1,
                'price': sign * inv.amount_retention,
                'account_id': account_id.id,
                'product_id': False,
                'uos_id': False,
                'account_analytic_id': False,
                'taxes': False,
            })

        return res

class account_invoice_tax(models.Model):
    _inherit = 'account.invoice.tax'
    
    @api.model
    def compute(self, invoice_id):
        order_ids = invoice_id.sale_order_ids or invoice_id.purchase_order_ids
        # Percent Additional Discount
        add_disc = invoice_id.add_disc
        # Percent Advance
        advance = not invoice_id.is_advance and order_ids and (order_ids[0].advance_percentage) or 0.0
        # Percent Deposit
        deposit_amount = not invoice_id.is_deposit and invoice_id.amount_deposit or 0.0
        deposit = order_ids and invoice_id.amount_net and (deposit_amount / (invoice_id.amount_net) * 100) or 0.0
        tax_grouped = super(account_invoice_tax, self).compute_ex(invoice_id, add_disc, advance, deposit)
        return tax_grouped

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
