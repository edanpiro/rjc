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
from lxml import etree

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_billing(models.Model):

    @api.model
    def _get_type(self):
        return self._context.get('type', False)
     
    @api.model
    def _get_period(self):
        if self._context.get('period_id', False):
            return self._context.get('period_id')
        periods = self.env['account.period'].find()
        return periods and periods[0] or False
         
    @api.model
    def _make_journal_search(self, ttype):
        journal_pool = self.env['account.journal']
        return journal_pool.search([('type', '=', ttype)], limit=1)
     
    @api.model
    def _get_journal(self):
        invoice_pool = self.env['account.invoice']
        journal_pool = self.env['account.journal']
        if self._context.get('invoice_id', False):
            currency_id = invoice_pool.browse(self._context['invoice_id']).currency_id.id
            journal_id = journal_pool.search([('currency', '=', currency_id)], limit=1)
            return journal_id and journal_id[0] or False
        if self._context.get('journal_id', False):
            return self._context.get('journal_id')
        if not self._context.get('journal_id', False) and self._context.get('search_default_journal_id', False):
            return self._context.get('search_default_journal_id')
 
        ttype = 'bank'
        res = self._make_journal_search(ttype)
        return res and res[0] or False
     
    @api.multi
    def _get_tax(self):
        journal_pool = self.env['account.journal']
        journal_id = self._context.get('journal_id', False)
        if not journal_id:
            ttype = self._context.get('type', 'bank')
            res = journal_pool.search([('type', '=', ttype)], limit=1)
            if not res:
                return False
            journal_id = res
 
        if not journal_id:
            return False
        journal = journal_id
        account_id = journal.default_credit_account_id or journal.default_debit_account_id
        if account_id and account_id.tax_ids:
            tax_id = account_id.tax_ids[0]
            return tax_id
        return False
     
    @api.model
    def _get_payment_rate_currency(self):
        """
        Return the default value for field payment_rate_currency_id: the currency of the journal
        if there is one, otherwise the currency of the user's company
        """
        journal_pool = self.env['account.journal']
        journal_id = self._context.get('journal_id', False)
        if journal_id:
            journal = journal_pool.browse(journal_id)
            if journal.currency:
                return journal.currency
        # no journal given in the context, use company currency as default
        return self.env.user.company_id.currency_id
     
    @api.model
    def _get_currency(self):
        journal_pool = self.env['account.journal']
        journal_id = self._context.get('journal_id', False)
        if journal_id:
            journal = journal_pool.browse(journal_id)
            if journal.currency:
                return journal.currency
     
    @api.model
    def _get_partner(self):
        return self._context.get('partner_id', False)
     
    @api.model
    def _get_reference(self):
        return self._context.get('reference', False)
     
    @api.model
    def _get_narration(self):
        return self._context.get('narration', False)
     
    @api.model
    def _get_amount(self):
        return self._context.get('amount', 0.0)
     
    @api.multi
    def name_get(self):
        if not self:
            return []
        return [(r['id'], (r['number'] or 'N/A')) for r in self.read(['number'], load='_classic_write')]
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        if view_type == 'form':
            if not view_id and self._context.get('invoice_type'):
                if self._context.get('invoice_type') in ('out_invoice', 'out_refund'):
                    result = self.env.ref('account_billing.view_vendor_receipt_form')
                else:
                    result = self.env.ref('account_billing.view_vendor_payment_form')
                result = result and result[1] or False
                view_id = result
            if not view_id and self._context.get('line_type'):
                if self._context.get('line_type') == 'customer':
                    result = self.env.ref('account_billing.view_vendor_receipt_form')
                else:
                    result = self.env('account_billing.view_vendor_payment_form')
                result = result and result[1] or False
                view_id = result
 
        res = super(account_billing, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
 
        if self._context.get('type', 'sale') in ('purchase', 'payment'):
            nodes = doc.xpath("//field[@name='partner_id']")
            for node in nodes:
                node.set('domain', "[('supplier', '=', True)]")
        res['arch'] = etree.tostring(doc)
        return res
     
    @api.multi
    def _compute_billing_amount(self, line_cr_ids, amount):
        credit = 0.0
        sign = 1
        for l in line_cr_ids:
            if isinstance(l, dict):
                credit += l['amount']
        return -(amount - sign * (credit))
    
    @api.onchange('line_cr_ids')
    def onchange_line_ids(self):
        if not self.line_cr_ids:
            return {'value':{}}
        line_osv = self.env["account.billing.line"]
        line_cr_ids = resolve_o2m_operations(line_osv, self.line_cr_ids, ['amount'])
        
        # compute the field is_multi_currency that is used to hide/display options linked to secondary currency on the billing
        is_multi_currency = False
        if self.currency_id:
            # if the billing currency is not False, it means it is different than the company currency and we need to display the options
            is_multi_currency = True
        else:
            # loop on the billing lines to see if one of these has a secondary currency. If yes, we need to define the options
            for billing_line in line_cr_ids:
                if billing_line:
                    company_currency = False
                    company_currency = billing_line.get('move_line_id', False) and self.env['account.move.line'].browse(billing_line.get('move_line_id')).company_id.currency_id.id
                    if billing_line.get('currency_id', company_currency) != company_currency:
                        is_multi_currency = True
                        break
        self.billing_amount = self._compute_billing_amount(self.line_cr_ids, self.amount)
        self.is_multi_currency = is_multi_currency
    



     
       
    @api.depends('line_cr_ids', 'line_cr_ids.amount')
    def _get_billing_amount(self):
        for billing in self:
            credit = 0.0
            sign = 1
            for l in billing.line_cr_ids:
                credit += l.amount

            currency = billing.currency_id or billing.company_id.currency_id
            self.billing_amount = - currency.round(billing.amount - sign * (credit)) 
    @api.one
    @api.depends('payment_rate')
    def _paid_amount_in_company_currency(self):
        rate = 1.0
        if self.currency_id:
            if self.company_id.currency_id.id == self.payment_rate_currency_id.id:
                rate = 1 / self.payment_rate
            else:
                ctx = dict(self._context or {})
                ctx.update({'date': self.date})
                billing_rate = self.currency_id.rate
                company_currency_rate = self.company_id.currency_id.rate
                rate = billing_rate * company_currency_rate
        self.paid_amount_in_company_currency = self.amount / rate
        
    _name = 'account.billing'
    _description = 'Accounting Billing'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'
    
    active = fields.Boolean('Active', help='', default=True)
#        'type':fields.selection([
#            ('receipt','Receipt'),
#        ],'Default Type', readonly=True, states={'draft':[('readonly',False)]}),
    name = fields.Char(string='Memo', readonly=True, default='', states={'draft':[('readonly', False)]})
    date = fields.Date(string='Date', readonly=True, select=True, default=time.strftime('%Y-%m-%d'), states={'draft':[('readonly', False)]}, help="Effective date for accounting entries")
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, default=_get_journal, readonly=True, states={'draft':[('readonly', False)]})
    
    account_id = fields.Many2one('account.account', string='Account', states={'draft':[('readonly', False)]})
    
    line_ids = fields.One2many('account.billing.line', 'billing_id', string='Billing Lines', readonly=True, states={'draft':[('readonly', False)]})
    
    line_cr_ids = fields.One2many('account.billing.line', 'billing_id', string='Credits', context={'default_type':'cr'}, states={'draft':[('readonly', False)]})
    
    period_id = fields.Many2one('account.period', string='Period', required=True, readonly=True, default=_get_period, states={'draft':[('readonly', False)]})
    narration = fields.Text(string='Notes', readonly=True, default=_get_narration,
                            states={'draft':[('readonly', False)]})
    currency_id = fields.Many2one(related='journal_id.currency', default=_get_currency, string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('account.billing'), readonly=True, states={'draft':[('readonly', False)]})
    state = fields.Selection(
                selection=[('draft', 'Draft'),
                 ('cancel', 'Cancelled'),
                 ('billed', 'Billed')], string='Status', default='draft', readonly=True,
                help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed billing. \
                    \n* The \'Billed\' status is used when user create billing,a billing number is generated \
                    \n* The \'Cancelled\' status is used when user cancel billing.')
    amount = fields.Float(string='Total', digits_compute=dp.get_precision('Account'),
                          default=_get_amount, required=True, readonly=True, states={'draft':[('readonly', False)]})
    tax_amount = fields.Float(string='Tax Amount', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft':[('readonly', False)]})
    reference = fields.Char(string='Ref #', readonly=True, default=_get_reference, states={'draft':[('readonly', False)]}, help="Transaction reference number.")
    number = fields.Char(string='Number', readonly=True,)
    # ktu, 'move_id':fields.many2one('account.move', 'Account Entry'),
    # ktu, 'move_ids': fields.related('move_id','line_id', type='one2many', relation='account.move.line', string='Journal Items', readonly=True),
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=1, readonly=True, default=_get_partner, states={'draft':[('readonly', False)]})
    # ktu, 'audit': fields.related('move_id','to_check', type='boolean', help='Check this box if you are unsure of that journal entry and if you want to note it as \'to be reviewed\' by an accounting expert.', relation='account.move', string='To Review'),
    # ktu, 'paid': fields.function(_check_paid, string='Paid', type='boolean', help="The billing has been totally paid."),
#        'pay_now':fields.selection([
#            ('pay_now','Pay Directly'),
#            ('pay_later','Pay Later or Group Funds'),
#        ],'Payment', select=True, readonly=True, states={'draft':[('readonly',False)]}),
    tax_id = fields.Many2one('account.tax', string='Tax', readonly=True, default=_get_tax, states={'draft':[('readonly', False)]}, domain=[('price_include', '=', False)], help="Only for tax excluded from price")
    # 'pre_line':fields.boolean('Previous Payments ?', required=False)
    date_due = fields.Date(string='Due Date', readonly=True, select=True, states={'draft':[('readonly', False)]})
    payment_option = fields.Selection(selection=[
                       ('without_writeoff', 'Keep Open'),
                       ('with_writeoff', 'Reconcile Payment Balance'),
                       ], string='Payment Difference', required=True, default='without_writeoff', readonly=True, states={'draft': [('readonly', False)]}, help="This field helps you to choose what you want to do with the eventual difference between the paid amount and the sum of allocated amounts. You can either choose to keep open this difference on the partner's account, or reconcile it with the payment(s)")
#        'writeoff_acc_id': fields.many2one('account.account', 'Counterpart Account', readonly=True, states={'draft': [('readonly', False)]}),
    comment = fields.Char(string='Counterpart Comment', required=True, default=_('Write-Off'), readonly=True, states={'draft': [('readonly', False)]})
#        'analytic_id': fields.many2one('account.analytic.account','Write-Off Analytic Account', readonly=True, states={'draft': [('readonly', False)]}),
    billing_amount = fields.Float(compute='_get_billing_amount', string='Billing Amount', store=True, readonly=True, help="Computed as the difference between the amount stated in the billing and the sum of allocation on the billing lines.")
    payment_rate_currency_id = fields.Many2one('res.currency', string='Payment Rate Currency', required=True, readonly=True, default=_get_payment_rate_currency, states={'draft':[('readonly', False)]})
    payment_rate = fields.Float(string='Exchange Rate', digits=(12, 6), default=1.0, required=True, readonly=True, states={'draft': [('readonly', False)]},
                                help='The specific rate that will be used, in this billing, between the selected currency (in \'Payment Rate Currency\' field)  and the billing currency.')
    paid_amount_in_company_currency = fields.Float(compute='_paid_amount_in_company_currency', string='Paid Amount in Company Currency', readonly=True)
    is_multi_currency = fields.Boolean(string='Multi Currency Billing', help='Fields with internal purpose only that depicts if the billing is a multi currency one or not')
    payment_id = fields.Many2one('account.voucher', string='Payment Ref#', required=False, readonly=True)
    
    @api.model    
    def create(self, vals):
        billing = super(account_billing, self).create(vals)
        billing.create_send_note()
        return billing
    
    @api.multi
    def compute_tax(self):
        tax_pool = self.env['account.tax']
        position_pool = self.env['account.fiscal.position']
 
        for billing in self:
            billing_amount = 0.0
            for line in billing.line_ids:
                billing_amount += line.untax_amount or line.amount
                line.amount = line.untax_amount or line.amount
                line.write({'amount':line.amount, 'untax_amount':line.untax_amount})
 
            if not billing.tax_id:
                self.write({'amount':billing_amount, 'tax_amount':0.0})
                continue
 
            tax = [billing.tax_id.id]
            partner = billing.partner_id.id
            taxes = position_pool.map_tax(partner and partner.property_account_position or False, tax)
            tax = tax_pool.browse(taxes)
 
            total = billing_amount
            total_tax = 0.0
 
            if not tax[0].price_include:
                for line in billing.line_ids:
                    for tax_line in tax_pool.compute_all(tax, line.amount, 1).get('taxes', []):
                        total_tax += tax_line.get('amount', 0.0)
                total += total_tax
            else:
                for line in billing.line_ids:
                    line_total = 0.0
                    line_tax = 0.0
 
                    for tax_line in tax_pool.compute_all(tax, line.untax_amount or line.amount, 1).get('taxes', []):
                        line_tax += tax_line.get('amount', 0.0)
                        line_total += tax_line.get('price_unit')
                    total_tax += line_tax
                    untax_amount = line.untax_amount or line.amount
                    line.write({'amount':line_total, 'untax_amount':untax_amount})
            billing.write({'amount': total, 'tax_amount': total_tax})
        return True
    
    @api.multi
    def onchange_price(self, line_ids, tax_id, partner_id=False):
        tax_pool = self.env['account.tax']
        partner_pool = self.env['res.partner']
        position_pool = self.env['account.fiscal.position']
        line_pool = self.env['account.billing.line']
        res = {
            'tax_amount': False,
            'amount': False,
        }
        billing_total = 0.0

        line_ids = resolve_o2m_operations(line_pool, line_ids, ['amount'])

        total_tax = 0.0
        for line in line_ids:
            line_amount = 0.0
            line_amount = line.get('amount', 0.0)

            if tax_id:
                tax = [tax_pool.browse(tax_id)]
                if partner_id:
                    partner = partner_pool.browse(partner_id) or False
                    taxes = position_pool.map_tax(partner and partner.property_account_position or False, tax)
                    tax = tax_pool.browse(taxes)

                if not tax[0].price_include:
                    for tax_line in tax.compute_all(line_amount, 1).get('taxes', []):
                        total_tax += tax_line.get('amount')

            billing_total += line_amount
        total = billing_total + total_tax

        res.update({
            'amount': total or billing_total,
            'tax_amount': total_tax
        })
        return {
            'value': res
        }
        
    @api.multi
    def onchange_term_id(self, term_id, amount):
        term_pool = self.env['account.payment.term']
        terms = False
        due_date = False
        default = {'date_due': False}
        if term_id and amount:
            terms = term_pool.compute(term_id, amount)
        if terms:
            due_date = terms[-1][0]
            default.update({
                'date_due':due_date
            })
        return {'value':default}
    
    @api.multi
    def onchange_rate(self, rate, amount, currency_id, payment_rate_currency_id, company_id):
        res = {}
        company_currency = self.company_id.currency_id
        if self.payment_rate and self.amount and self.currency_id:  # and currency_id == payment_rate_currency_id:
            billing_rate = self.env['res.currency'].browse(currency_id).rate
            if company_currency.id == self.payment_rate_currency_id.id:
                company_rate = self.payment_rate
            else:
                company_rate = self.env['res.company'].browse(company_id).currency_id.rate
            res['value']['paid_amount_in_company_currency'] = amount / billing_rate * company_rate
        return res

    @api.multi
    def recompute_payment_rate(self, vals, currency_id, date, journal_id, amount):
        # on change of the journal, we need to set also the default value for payment_rate and payment_rate_currency_id
        currency_obj = self.env['res.currency']
        journal = self.env['account.journal'].browse(journal_id)
        company_id = journal.company_id.id
        payment_rate = 1.0
        payment_rate_currency_id = currency_id
        ctx = self._context.copy()
        ctx.update({'date': date})
        o2m_to_loop = 'line_cr_ids'
        if o2m_to_loop and 'value' in vals and o2m_to_loop in vals['value']:
            for billing_line in vals['value'][o2m_to_loop]:
		if not isinstance(billing_line, dict):
                    continue
                if billing_line['currency_id'] != currency_id:
                    # we take as default value for the payment_rate_currency_id, the currency of the first invoice that
                    # is not in the billing currency
                    payment_rate_currency_id = billing_line['currency_id']
                    tmp = currency_obj.browse(payment_rate_currency_id).rate
                    billing_currency_id = currency_id or journal.company_id.currency_id.id
                    payment_rate = tmp / currency_obj.browse(billing_currency_id).rate
                    break
        res = self.with_context(ctx).onchange_rate(payment_rate, amount, currency_id, payment_rate_currency_id, company_id)
        for key in res.keys():
            vals[key].update(res[key])
        vals['value'].update({'payment_rate': payment_rate})
        if payment_rate_currency_id:
            vals['value'].update({'payment_rate_currency_id': payment_rate_currency_id})
        return vals
    
    @api.multi
    def onchange_partner_id(self, partner_id, journal_id, amount, currency_id, date):
        # Additional Condition for Matching Billing Date
        ctx = dict(self._context)
        ctx.update({'billing_date_condition': ['|', ('date_maturity', '=', False), ('date_maturity', '<=', date)]})
        if not journal_id:
            return {}
        res = self.with_context(ctx).recompute_billing_lines(partner_id, journal_id, amount, currency_id, date)
        vals = self.with_context(ctx).recompute_payment_rate(res, currency_id, date, journal_id, amount)
        for key in vals.keys():
            res[key].update(vals[key])
        return res
    
    @api.model
    def recompute_billing_lines(self, partner_id, journal_id, price, currency_id, date):
        """
        Returns a dict that contains new values and context
 
        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone
 
        @return: Returns a dict which contains new values, and context
        """
        def _remove_noise_in_o2m():
            """if the line is partially reconciled, then we must pay attention to display it only once and
                in the good o2m.
                This function returns True if the line is considered as noise and should not be displayed
            """
            if line.reconcile_partial_id:
                sign = 1
                if currency_id == line.currency_id.id:
                    if line.amount_residual_currency * sign <= 0:
                        return True
                else:
                    if line.amount_residual * sign <= 0:
                        return True
            return False
 
        billing_date_condition = self._context.get('billing_date_condition', [])
        context_multi_currency = self._context.copy()
        if date:
            context_multi_currency.update({'date': date})
 
        move_line_pool = self.env['account.move.line']
        partner_pool = self.env['res.partner']
        journal_pool = self.env['account.journal']
        line_pool = self.env['account.billing.line']
 
        # set default values
        default = {
            'value': {'line_cr_ids': [] },
        }
 
        # drop existing lines
        line_ids = line_pool.search([('billing_id', '=', self.id)])
        #if line_ids:
            #line_ids.unlink()
        for line in line_ids:
            if line.type == 'cr':
                default['value']['line_cr_ids'].append((2, line.id))
            else:
                default['value']['line_dr_ids'].append((2, line.id))
 
        if not partner_id or not journal_id:
            return default
        
        journal = journal_pool.browse(journal_id)
        partner = partner_pool.browse(partner_id)
        currency_id = currency_id or journal.company_id.currency_id
        account_id = False
        if journal.type in ('sale', 'sale_refund'):
            account_id = partner.property_account_receivable.id
        elif journal.type in ('purchase', 'purchase_refund', 'expense'):
            account_id = partner.property_account_payable.id
        else:
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id
 
        default['value']['account_id'] = account_id
 
        if journal.type not in ('cash', 'bank'):
            return default
 
        total_credit = price or 0.0
        account_type = 'receivable'
 
        if not self._context.get('move_line_ids', False):
            move_lines = move_line_pool.search(
                                        [('state', '=', 'valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id),
                                         ] + billing_date_condition,
                                        )
        else:
            move_lines = self._context['move_line_ids']
        invoice_id = self._context.get('invoice_id', False)
        company_currency = journal.company_id.currency_id
        move_line_found = False
 
        # order the lines by most old first
        move_lines.ids.reverse()
        account_move_lines = move_line_pool.browse(move_lines.ids)
 
        # compute the total debit/credit and look for a matching open amount or invoice
        for line in account_move_lines:
            if _remove_noise_in_o2m():
                continue
 
            if invoice_id:
                if line.invoice.id == invoice_id:
                    # if the invoice linked to the billing line is equal to the invoice_id in context
                    # then we assign the amount on that line, whatever the other billing lines
                    move_line_found = line.id
                    break
            elif currency_id.id == company_currency.id:
                # otherwise treatments is the same but with other field names
                if line.amount_residual == price:
                    # if the amount residual is equal the amount billing, we assign it to that billing
                    # line, whatever the other billing lines
                    move_line_found = line.id
                    break
                # otherwise we will split the billing amount on each line (by most old first)
                total_credit += line.credit or 0.0
            elif currency_id.id == line.currency_id.id:
                if line.amount_residual_currency == price:
                    move_line_found = line.id
                    break
                total_credit += line.credit and line.amount_currency or 0.0
 
        # billing line creation
        for line in account_move_lines:
 
            if _remove_noise_in_o2m():
                continue
 
            if line.currency_id and currency_id == line.currency_id.id:
                amount_original = abs(line.amount_currency)
                amount_unreconciled = abs(line.amount_residual_currency)
            else:
                amount_original = company_currency.compute(line.credit or 0.0, currency_id)
                amount_unreconciled = company_currency.compute(abs(line.amount_residual), currency_id)
            line_currency_id = line.currency_id and line.currency_id.id or company_currency.id
            rs = {
                'move_line_id':line.id,
                'type': line.credit and 'dr' or 'cr',
                'reference':line.invoice.reference,
                'account_id':line.account_id.id,
                'amount_original': amount_original,
                'amount': (move_line_found == line.id) and min(abs(price), amount_unreconciled) or amount_unreconciled,
                'date_original':line.date,
                'date_due':line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'currency_id': line_currency_id,
            }
             
            # Negate DR records
            if rs['type'] == 'dr':
                rs['amount_original'] = -rs['amount_original']
                rs['amount'] = -rs['amount']
                rs['amount_unreconciled'] = -rs['amount_unreconciled']
 
            if rs['amount_unreconciled'] == rs['amount']:
                rs['reconcile'] = True
            else:
                rs['reconcile'] = False
                
            default['value']['line_cr_ids'].append(rs)
 
#            if ttype == 'payment' and len(default['value']['line_cr_ids']) > 0:
#                default['value']['pre_line'] = 1
#            elif ttype == 'receipt' and len(default['value']['line_dr_ids']) > 0:
#                default['value']['pre_line'] = 1
            default['value']['billing_amount'] = self._compute_billing_amount(default['value']['line_cr_ids'], price)
        return default
    
    @api.multi
    def onchange_payment_rate_currency(self, currency_id, payment_rate, payment_rate_currency_id, date, amount, company_id):
        res = {'value': {}}
        # set the default payment rate of the billing and compute the paid amount in company currency
        if currency_id and currency_id == payment_rate_currency_id:
            ctx = self._context.copy()
            ctx.update({'date': date})
            vals = self.with_context(ctx).onchange_rate(payment_rate, amount, currency_id, payment_rate_currency_id, company_id)
            for key in vals.keys():
                res[key].update(vals[key])
        return res
    
    @api.multi
    def onchange_date(self, date, currency_id, payment_rate_currency_id, amount, company_id):
        """
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        res = {'value': {}}
        # set the period of the billing
        period_pool = self.env['account.period']
        currency_obj = self.env['res.currency']
        ctx = dict(self._context)
        ctx.update({'company_id': company_id})
        pids = period_pool.with_context(ctx).find(date)
        if pids:
            res['value'].update({'period_id':pids[0]})
        if payment_rate_currency_id:
            ctx.update({'date': date})
            payment_rate = 1.0
            if payment_rate_currency_id != currency_id:
                tmp = currency_obj.with_context(ctx).browse(payment_rate_currency_id).rate
                billing_currency_id = currency_id or self.env['res.company'].browse(company_id).currency_id.id
                payment_rate = tmp / currency_obj.browse(billing_currency_id).rate
            vals = self.onchange_payment_rate_currency(currency_id, payment_rate, payment_rate_currency_id, date, amount, company_id)
            vals['value'].update({'payment_rate': payment_rate})
            for key in vals.keys():
                res[key].update(vals[key])
         
        res2 = self.onchange_partner_id(ctx.get('partner_id'), ctx.get('journal_id'), amount, currency_id, date)
        if res2:
            for key in res2.keys():
                res[key].update(res2[key])
        return res
    
    @api.multi
    def onchange_journal(self, journal_id, line_ids, tax_id, partner_id, date, amount, company_id, context=None):
        if not journal_id:
            return False
        journal_pool = self.env['account.journal']
        journal = journal_pool.browse(journal_id)
        vals = {'value':{}}
        currency_id = False
        if journal.currency:
            currency_id = journal.currency.id
        vals['value'].update({'currency_id': currency_id})
        res = self.onchange_partner_id(partner_id, journal_id, amount, currency_id, date)
        if res:
            for key in res.keys():
                vals[key].update(res[key])
        return vals
     
    @api.multi
    def button_proforma_billing(self):
        for vid in self:
            vid.signal_workflow('proforma_billing')
        return {'type': 'ir.actions.act_window_close'}
 
    # KTU
    @api.multi
    def validate_billing(self):
        self.write({ 'state': 'billed' })
        self.write({ 'number': self.env['ir.sequence'].get('account.billing') })
        self.message_post(body=_('Billing is billed.'))
        return True
    # KTU
    
    @api.multi
    def action_cancel_draft(self):
        for billing_id in self:
            billing_id.delete_workflow()
            billing_id.create_workflow()
        self.write({'state':'draft'})
        self.message_post(body=_('Billing is reset to draft'))
        return True
    
    # KTU
    @api.multi
    def cancel_billing(self):
        self.write({ 'state': 'cancel' })
        self.message_post(body=_('Billing is cancelled.'))
        return True
 
    # KTU
    @api.multi
    def unlink(self):
        for t in self.read(['state']):
            if t['state'] not in ('draft', 'cancel'):
                raise Warning(_('Invalid Action!'), _('Cannot delete billing(s) which are already billed.'))
        return super(account_billing, self).unlink()
    
    @api.multi
    def _sel_context(self):
        """
        Select the context to use accordingly if it needs to be multicurrency or not.
 
        :param billing_id: Id of the actual billing
        :return: The returned context will be the same as given in parameter if the billing currency is the same
                 than the company currency, otherwise it's a copy of the parameter with an extra key 'date' containing
                 the date of the billing.
        :rtype: dict
        """
        company_currency = self._get_company_currency()
        current_currency = self._get_current_currency()
        if current_currency <> company_currency:
            context_multi_currency = dict(self._context)
            context_multi_currency.update({'date': self.date})
            return context_multi_currency
        return dict(self._context)
    
    @api.multi
    def _convert_amount(self, amount):
        '''
        This function convert the amount given in company currency. It takes either the rate in the billing (if the
        payment_rate_currency_id is relevant) either the rate encoded in the system.
 
        :param amount: float. The amount to convert
        :param billing: id of the billing on which we want the conversion
        :param context: to context to use for the conversion. It may contain the key 'date' set to the billing date
            field in order to select the good rate to use.
        :return: the amount in the currency of the billing's company
        :rtype: float
        '''
        currency_obj = self.env['res.currency']
        res = amount
        if self.payment_rate_currency_id.id == self.company_id.currency_id.id:
            # the rate specified on the billing is for the company currency
            res = currency_obj.round((amount * self.payment_rate))
        else:
            # the rate specified on the billing is not relevant, we use all the rates in the system
            res = currency_obj.compute(amount)
        return res
    
    @api.multi
    def _get_company_currency(self, billing_id):
        '''
        Get the currency of the actual company.
 
        :param billing_id: Id of the billing what i want to obtain company currency.
        :return: currency id of the company of the billing
        :rtype: int
        '''
        return self.env['account.billing'].browse(billing_id).journal_id.company_id.currency_id.id
    
    @api.multi
    def _get_current_currency(self, billing_id):
        '''
        Get the currency of the billing.
 
        :param billing_id: Id of the billing what i want to obtain current currency.
        :return: currency id of the billing
        :rtype: int
        '''
        billing = self.env['account.billing'].browse(billing_id)
        return billing.currency_id.id or self._get_company_currency(billing.id)
    
    @api.multi
    def copy(self, default=None):
        if default is None:
            default = {}
        default.update({
            'state': 'draft',
            'number': False,
            'line_cr_ids': False,
            'reference': False
        })
        if 'date' not in default:
            default['date'] = time.strftime('%Y-%m-%d')
        return super(account_billing, self).copy(default)
 
    # -----------------------------------------
    # OpenChatter notifications and need_action
    # -----------------------------------------
    _document_type = {
        'payment': 'Supplier Billing',
        'receipt': 'Customer Billing',
        False: 'Payment',
    }
    
    @api.multi
    def create_send_note(self):
        message = "Billing Document <b>created</b>."
        self.message_post(body=message, subtype="account_billing.mt_billing")
    
    @api.multi
    def post_send_note(self):
        message = "%s '%s' is <b>posted</b>." % (self._document_type[self.type or False], self.move_id.name)
        self.message_post(body=message, subtype="account_billing.mt_billing")
            
    @api.multi
    def reconcile_send_note(self):
        message = "%s <b>reconciled</b>." % self._document_type[self.type or False]
        self.message_post(body=message, subtype="account_billing.mt_billing")

class account_billing_line(models.Model):
    _name = 'account.billing.line'
    _description = 'Billing Lines'
    _order = "move_line_id"

    # If the payment is in the same currency than the invoice, we keep the same amount
    # Otherwise, we compute from company currency to payment currency
    @api.one
    @api.depends('billing_id')
    def _compute_balance(self):
        ctx = dict(self._context)
        ctx.update({'date': self.billing_id.date})
        company_currency = self.billing_id.journal_id.company_id.currency_id
        billing_currency = self.billing_id.currency_id and self.billing_id.currency_id or company_currency
        move_line = self.move_line_id or False

        if not move_line:
            self.amount_original = 0.0
            self.amount_unreconciled = 0.0
        elif move_line.currency_id and billing_currency.id == move_line.currency_id.id:
            self.amount_original = move_line.currency_id.with_context(ctx).compute(abs(move_line.amount_currency), billing_currency)
            self.amount_unreconciled = move_line.currency_id.with_context(ctx).compute(abs(move_line.amount_residual_currency), billing_currency)
        elif move_line and move_line.credit > 0:
            self.amount_original = company_currency.with_context(ctx).compute(move_line.credit,billing_currency)
            self.amount_unreconciled = company_currency.compute(abs(move_line.amount_residual), billing_currency)
        else:
            self.amount_original = company_currency.with_context(ctx).compute(move_line.debit, billing_currency)
            self.amount_unreconciled = company_currency.with_context(ctx).compute(abs(move_line.amount_residual), billing_currency)
    
    @api.one
    @api.depends('billing_id', 'move_line_id')
    def _currency_id(self):
        '''
        This function returns the currency id of a billing line. It's either the currency of the
        associated move line (if any) or the currency of the billing or the company currency.
        '''
        move_line = self.move_line_id
        if move_line:
            self.currency_id = move_line.currency_id and move_line.currency_id or move_line.company_id.currency_id.id
        else:
            self.currency_id = self.billing_id.currency_id and self.billing_id.currency_id or self.billing_id.company_id.currency_id.id
        
    billing_id = fields.Many2one('account.billing', 'billing', required=1, ondelete='cascade')
    name = fields.Char(string='Description', default='')
    reference = fields.Char(string='Invoice Reference', help='The partner reference of this invoice.')
    account_id = fields.Many2one('account.account', string='Account', readonly=True, required=True)
    partner_id = fields.Many2one('res.partner', related='billing_id.partner_id', string='Partner')
    untax_amount = fields.Float(string='Untax Amount')
    amount = fields.Float(string='Amount', digits_compute=dp.get_precision('Account'))
    reconcile = fields.Boolean(string='Full Reconcile')
    type = fields.Selection(selection=[('dr', 'Debit'), ('cr', 'Credit')], string='Dr/Cr')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    move_line_id = fields.Many2one('account.move.line', string='Journal Item')
    date_original = fields.Date(string='Date', readonly=1)  # related='move_line_id.date', 
    date_due = fields.Date(related='move_line_id.date_maturity', string='Due Date', readonly=1, store=True)
    amount_original = fields.Float(compute='_compute_balance', string='Original Amount', store=True, digits_compute=dp.get_precision('Account'))
    amount_unreconciled = fields.Float(compute='_compute_balance', string='Open Balance', store=True, digits_compute=dp.get_precision('Account'))
    company_id = fields.Many2one(related='billing_id.company_id', string='Company', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', compute='_currency_id', string='Currency', comodel='res.currency', readonly=True)
        
    @api.multi
    def onchange_reconcile(self, reconcile, amount, amount_unreconciled):
        vals = {'amount': 0.0}
        if reconcile:
            vals = {'amount': amount_unreconciled}
        return {'value': vals}
    
    @api.multi
    def onchange_amount(self, reconcile, amount, amount_unreconciled):
        vals = {}
        if amount == amount_unreconciled:
            vals = {'reconcile': True}
        else:
            vals = {'reconcile': False, 'amount':0.0}
        return {'value': vals}
    
    @api.model
    def default_get(self, fields_list):
        partner_id = self._context.get('partner_id', False)
        partner_pool = self.env['res.partner']
        
        account_id = False
        values = super(account_billing_line, self).default_get(fields_list)
        if ('account_id' not in fields_list):
            return values
         
        if partner_id:
            partner = partner_pool.browse(partner_id)
            account_id = partner.property_account_receivable.id
 
        values.update({
            'account_id':account_id,
        })
        return values

def resolve_o2m_operations(target_osv, operations, fields):
    results = []
    for operation in operations:
        result = None
        if not isinstance(operation, (list, tuple)):
            result = target_osv.read(operation, fields)
        elif operation[0] == 0:
            # may be necessary to check if all the fields are here and get the default values?
            result = operation[2]
        elif operation[0] == 1:
            result = target_osv.read(operation[1], fields)
            if not result: result = {}
            result.update(operation[2])
        elif operation[0] == 4:
            result = target_osv.read(operation[1], fields)
        if result != None:
            results.append(result)
    return results

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
