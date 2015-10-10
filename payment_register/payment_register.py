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
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning

class payment_register(models.Model):
    
    @api.model
    def _get_reference(self):
        return self._context.get('reference', False)
    
    @api.model
    def _get_narration(self):
        return self._context.get('narration', False)
    
    @api.model
    def _make_journal_search(self, ttype):
        journal_pool = self.env['account.journal']
        return journal_pool.search([('type', '=', ttype)], limit=1)
    
    @api.model
    def _get_exchange_rate_currency(self):
        """
        Return the default value for field original_pay_currency_id: the currency of the journal
        if there is one, otherwise the currency of the user's company
        """
        journal_pool = self.env['account.journal']
        journal_id = self._context.get('journal_id', False)
        if journal_id:
            journal = journal_pool.browse(journal_id)
            if journal.currency:
                return journal.currency.id
        # no journal given in the context, use company currency as default
        return self.env.user.company_id.currency_id.id
    
    @api.multi
    def _paid_amount_in_company_currency(self):
        rate = 1.0
        for register in self:
            if register.currency_id:
                if register.company_id.currency_id.id == register.original_pay_currency_id.id:
                    if register.exchange_rate == 0.0:
                        register.exchange_rate = 1.0
                    rate = 1 / register.exchange_rate
                else:
                    ctx = dict(self._context)
                    ctx.update({'date': register.date})
                    voucher_rate = register.with_context(ctx).currency_id.rate
                    company_currency_rate = register.company_id.currency_id.rate
                    rate = voucher_rate * company_currency_rate
                    if rate == 0:
                        rate = 1
            register.paid_amount_in_company_currency = register.amount / rate

    _name = 'payment.register'
    _description = 'Payment Register'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'
    _rec_name = 'number'

    # Document
    number = fields.Char(string='Number', readonly=True, copy=False)
    # Header Information from Payment document
    voucher_id = fields.Many2one('account.voucher', string='Customer Payment', readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one(related='voucher_id.partner_id', string='Partner', store=True, readonly=True)
    date_payment = fields.Date(related='voucher_id.date', string='Payment Date', store=True, readonly=True)
    journal_transit_id = fields.Many2one(related='voucher_id.journal_id', string='Payment in Transit', store=True, readonly=True)
    account_transit_id = fields.Many2one(related='voucher_id.account_id', string='Account in Transit', store=True, readonly=True)
    original_pay_currency_id = fields.Many2one('res.currency', string='Original Payment Currency', required=True, readonly=True,
                                               default=_get_exchange_rate_currency, states={'draft': [('readonly', False)]})
    amount_pay_total = fields.Float(related='voucher_id.amount', string='Payment Total', store=True, readonly=True)
    original_pay_amount = fields.Float(string='Original Pay Amount', digits_compute=dp.get_precision('Account'), required=True, readonly=True, states={'draft': [('readonly', False)]}, default=0.0)
    # Company Information
    company_id = fields.Many2one(related='voucher_id.company_id', string='Company', store=True, readonly=True, default=lambda self: self.env['res.company']._company_default_get('payment.register'))
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', store=True, readonly=True)
    paid_amount_in_company_currency = fields.Float(compute='_paid_amount_in_company_currency', string='Paid Amount in Company Currency', readonly=True)
    memo = fields.Char(string='Memo', readonly=True, states={'draft': [('readonly', False)]})
    reference = fields.Char(string='Ref #', readonly=True, states={'draft': [('readonly', False)]}, help='Transaction reference number.')
    # Multi Currency from Original Currency to Target Currency
    is_multi_currency = fields.Boolean(string='Multi Currency Voucher', help='Fields with internal purpose only that depicts if the voucher is a multi currency one or not')
    exchange_rate = fields.Float(string='Exchange Rate', digits=(12, 6), required=True, readonly=True, states={'draft': [('readonly', False)]}, default=1.0)
    exchange_rate_payin = fields.Float(string='Exchange Rate Payin', digits=(12, 6), required=True, readonly=True, default=1.0, states={'draft': [('readonly', False)]},)
#     # Payment Detail
    pay_detail_id = fields.Many2one('account.voucher.pay.detail', string='Payment Detail Ref', ondelete='restrict', select=True)
    name = fields.Char(string='Bank/Branch', readonly=True, states={'draft': [('readonly', False)]})
    type = fields.Selection(selection=[
                ('check', 'Check'),
                ('cash', 'Cash'),
                ('transfer', 'Transfer'),
                ], string='Type', required=True, readonly=True, states={'draft': [('readonly', False)]})
    check_no = fields.Char(string='Check No.', readonly=True, states={'draft': [('readonly', False)]})
    date_due = fields.Date(string='Date Due', readonly=True, states={'draft': [('readonly', False)]})
    amount = fields.Float(string='Amount', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft': [('readonly', False)]})
    # Payment Register
    date = fields.Date(string='Pay-in Date', readonly=True, default=time.strftime('%Y-%m-%d'), select=True, states={'draft': [('readonly', False)]}, help="Effective date for accounting entries")
    period_id = fields.Many2one('account.period', string='Period', readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', string='Target Bank', readonly=True, states={'draft': [('readonly', False)]})
    account_id = fields.Many2one('account.account', string='Account', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, states={'draft': [('readonly', False)]})
    amount_payin = fields.Float(string='Pay-in Amount', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft': [('readonly', False)]})
    # Miscellenous
    narration = fields.Text(string='Notes', default=_get_narration)
    state = fields.Selection(
                selection=[('draft', 'Draft'),
                 ('cancel', 'Cancelled'),
                 ('posted', 'Posted'),
                 ('bounce_check', 'Bounced Check'),
                ], string='Status', readonly=True, default='draft',
                help=' * Th1.0e \'Draft\' status is used when a user is encoding a new and unconfirmed payment register. \
                            \n* The \'Posted\' status is used when user create payment register,a Register number is generated and accounting entries are created in account \
                            \n* The \'Cancelled\' status is used when user cancel payment register.')
    move_id = fields.Many2one('account.move', string='Account Entry', copy=False)
    move_ids = fields.One2many(related='move_id.line_id', string='Journal Items', readonly=True)
    # Diff
    # 'writeoff_amount': fields.function(_get_writeoff_amount, string='Difference Amount', type='float', readonly=True, help="Computed as the difference between the amount stated in the voucher and the sum of allocation on the voucher lines."),
    writeoff_amount = fields.Float(string='Diff Amount', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft': [('readonly', False)]}, help="Computed as the difference between the amount stated in the Payment Detail and the Payment Register.")
    writeoff_amount_local = fields.Float(string='Diff Amount (local)', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft': [('readonly', False)]}, help="Computed as the difference between the amount stated in the Payment Detail and the Payment Register.")
    gainloss_amount = fields.Float(string='Gain / Loss', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft': [('readonly', False)]})
    payment_option = fields.Selection(selection=[('with_writeoff', 'Reconcile Payment Balance')], default='with_writeoff', string='Payment Difference', required=True, readonly=True, states={'draft': [('readonly', False)]}, help="This field helps you to choose what you want to do with the eventual difference between the paid amount and the sum of allocated amounts. You can either choose to keep open this difference on the partner's account, or reconcile it with the payment(s)")
    writeoff_acc_id = fields.Many2one('account.account', string='Counterpart Account', required=False, readonly=True, states={'draft': [('readonly', False)]})
    comment = fields.Char(string='Counterpart Comment' , default=_('Write-Off'))
    new_register_id = fields.Many2one('payment.register', string='New Payment Detail', readonly=True, help='This new Payment Register is created to replace the one with bounced check.')

    @api.model
    def create(self, vals):
        register = super(payment_register, self).create(vals)
        register.create_send_note()
        return register
 
    @api.multi
    def unlink(self):
        for t in self.read(['state']):
            if t['state'] not in ('draft', 'cancel'):
                raise Warning(_('Invalid Action!'), _('Cannot delete voucher(s) which are already opened or paid.'))
        return super(payment_register, self).unlink()
     
    @api.one
    def copy(self, default=None):
        if self._context.get('bounce_check', False):
            if default is None:
                default = {}
                
            default.update({
                'state': 'draft',
                'line_cr_ids': False,
                'line_dr_ids': False,
            })
            if 'date' not in default:
                default['date'] = time.strftime('%Y-%m-%d')
            return super(payment_register, self).copy(default)
        else:
            raise Warning(_('Error!'), _('Duplication of Payment Detail not allowed. If this payment detail is cancelled, and you want to renew, use "Set to Draft" instead.'))
     
    @api.multi
    def create_send_note(self):
        message = 'Payment Register <b>created</b>.'
        self.message_post(body=message, subtype='payment_register.mt_register')
     
    @api.model
    def post_send_note(self):
        message = "Payment Register '%s' is <b>posted</b>." % self.move_id.name
        self.message_post(body=message, subtype="payment_register.mt_register")
     
    @api.multi
    def validate_register(self):
        if not self.journal_id.id or not self.date:
            raise Warning(_('Warning!'), _('Pay-in Date and Target Bank is not selected.'))
        self.action_move_line_create()
        return True
     
    @api.multi
    def register_move_line_create(self, register_id, move_id, company_currency, current_currency):
        move_line_obj = self.env['account.move.line']
        register_brw = self.env['payment.register'].browse(register_id)
        ctx = dict(self._context)
        ctx.update({'date': register_brw.date})
        amount = self.with_context(ctx)._convert_amount(register_brw.amount_payin, register_brw.id)
        move_line = {
            'journal_id': register_brw.journal_id.id,
            'period_id': register_brw.period_id.id,
            'name': register_brw.name or '/',
            'account_id': register_brw.account_id and register_brw.account_id.id or False, 
            'move_id': move_id.id,
            'partner_id': register_brw.partner_id.id,
            'currency_id': company_currency != current_currency and current_currency or False,
            # 'analytic_account_id': register_brw.account_analytic_id and register_brw.account_analytic_id.id or False,
            'amount_currency': company_currency != current_currency and register_brw.amount_payin or 0.0,
            'quantity': 1,
            'credit': amount < 0 and -amount or 0.0,
            'debit': amount > 0 and amount or 0.0,
            'date': register_brw.date
        }
        move_line_id = move_line_obj.create(move_line)
        return move_line_id
     
    @api.multi
    def writeoff_move_line_create(self, register, move_id, company_currency, current_currency):
        if not register.writeoff_amount_local:
            return False
        amount = register.writeoff_amount_local
        move_line = {
            'journal_id': register.journal_id.id,
            'period_id': register.period_id.id,
            'name': register.name or '/',
            'account_id': register.writeoff_acc_id.id,
            'move_id': move_id.id,
            'partner_id': register.partner_id.id,
            'currency_id': company_currency != current_currency and current_currency or False,
            # 'analytic_account_id': register_brw.account_analytic_id and register_brw.account_analytic_id.id or False,
            'amount_currency': company_currency != current_currency and register.writeoff_amount or 0.0,
            'quantity': 1,
            'credit': amount < 0 and -amount or 0.0,
            'debit': amount > 0 and amount or 0.0,
            'date': register.date
        }
        move_line_id = self.env['account.move.line'].create(move_line)
        return move_line_id
     
    @api.multi
    def gainloss_move_line_create(self, register, move_id):
        company = register.company_id
        ctx = dict(self._context)
        ctx.update({'date': register.date})
        amount_payin_company_currency = self.with_context(ctx)._convert_amount(register.amount_payin, register.id)
        # make the rounding as defined in company currency.
        amount_payin_company_currency = company.currency_id.round(amount_payin_company_currency)
        paid_amount_in_company_currency = company.currency_id.round(register.paid_amount_in_company_currency)
        writeoff_amount_local = company.currency_id.round(register.writeoff_amount_local)
        # amount to post
        amount = amount_payin_company_currency - paid_amount_in_company_currency + writeoff_amount_local
        if abs(amount) < 10 ** -4:            
            return False
        if not company.income_currency_exchange_account_id or not company.expense_currency_exchange_account_id:
            raise Warning(_('Accounting Error !'),
                _('Gain/Loss Exchange Rate Account is not setup properly! Please see Settings > Configuration > Accounting.'))            
        move_line = {
            'journal_id': register.journal_id.id,
            'period_id': register.period_id.id,
            'name': register.name or '/',
            'account_id': amount > 0 and company.income_currency_exchange_account_id.id or company.expense_currency_exchange_account_id.id,
            'move_id': move_id.id,
            'partner_id': register.partner_id.id,
            'currency_id': False,
            # 'analytic_account_id': register_brw.account_analytic_id and register_brw.account_analytic_id.id or False,
            'amount_currency': 0.0,
            'quantity': 1,
            'credit': amount > 0 and amount or 0.0,
            'debit': amount < 0 and -amount or 0.0,
            'date': register.date
        }
        move_line_id = self.env['account.move.line'].create(move_line)
        # Assign amount to gainloss_amount field
        register.write({'gainloss_amount': amount})
        return move_line_id
     
    @api.multi
    def action_move_line_create(self):
        '''
        Confirm the register given in ids and create the journal entries for each of them
        '''
        move_pool = self.env['account.move']
        move_line_pool = self.env['account.move.line']
        for register in self:
            if register.move_id:
                continue
            company_currency = self._get_company_currency(register.id)
            current_currency = self._get_current_currency(register.id)
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(register.id)
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = (context.copy())
            ctx['date'] = register.date
            # Create the account move record.
            move_id = move_pool.create(self.account_move_get(register.id))
            # Get the name of the account_move just created
            name = move_id.name
            # Create the first line of the register
            move_line_pool.create(self.first_move_line_get(register.id, move_id.id, company_currency, current_currency))
            # Create one move line per register line where amount is not 0.0
            self.register_move_line_create(register.id, move_id, company_currency, current_currency)
            # Create the writeoff/gainloss line if needed
            self.writeoff_move_line_create(register, move_id, company_currency, current_currency)
            self.gainloss_move_line_create(register, move_id)
            # We post the register.
            register.write({
                'move_id': move_id.id,
                'state': 'posted',
                'number': name,
            })
            register.post_send_note()
            if register.journal_id.entry_posted:
                move_id.post()
        return True
     
    @api.multi
    def onchange_journal_date(self, journal_id, original_pay_amount, original_pay_currency_id, company_id, amount, amount_payin, date):
        if not journal_id:
            return False
        # Set Account and Currency
        currency_obj = self.env['res.currency']
        journal_pool = self.env['account.journal']
        journal = journal_pool.browse(journal_id)
        account_id = journal.default_debit_account_id.id or journal.default_credit_account_id.id
        currency = journal.currency or journal.company_id.currency_id
        original_pay_currency = currency_obj.browse(original_pay_currency_id)
        vals = {'value': {}}
        vals['value'].update({'account_id': account_id})
        vals['value'].update({'currency_id': currency.id})
        # Compute Payment Rate
        ctx = dict(self._context)
        ctx.update({'date': self.date_payment})
        exchange_rate = currency_obj.with_context(ctx)._get_conversion_rate(currency, original_pay_currency)
        ctx.update({'date': self.date})
        exchange_rate_payin = currency_obj.with_context(ctx)._get_conversion_rate(currency, original_pay_currency)
        vals['value'].update({'exchange_rate': exchange_rate})
        vals['value'].update({'exchange_rate_payin': exchange_rate_payin})
        # Compute period
        period_pool = self.env['account.period']
        ctx.update({'company_id': self.company_id.id})
        pids = period_pool.with_context(ctx).find(self.date)
        if pids:
            vals['value'].update({'period_id': pids.id})
        # Compute Amount
        res = self.onchange_rate(exchange_rate, exchange_rate_payin, amount, amount_payin, original_pay_amount)
        for key in res.keys():
            vals[key].update(res[key])
        return vals
      
    @api.multi
    def onchange_date(self, journal_id, original_pay_amount, original_pay_currency_id, company_id, amount, amount_payin, date):
        res = {'value': {}}
        # set the period of the register
        period_pool = self.env['account.period']
        ctx = dict(self._context)
        ctx.update({'company_id': company_id})
        pids = period_pool.with_context(ctx).find(date)
        if pids:
            res['value'].update({'period_id': pids[0]})
        return res
  
    @api.multi
    def onchange_rate(self, exchange_rate, exchange_rate_payin, amount, amount_payin, original_pay_amount, context=None):
        res = {'value': {}}
        amount = exchange_rate and float(original_pay_amount) / float(exchange_rate) or float(amount)
        amount_payin = exchange_rate_payin and float(original_pay_amount) / float(exchange_rate_payin) or float(amount_payin)
        res['value'].update({
            'amount': amount,
            'amount_payin': amount_payin,
        })
        return res
      
    @api.multi
    def onchange_amount(self, field, amount, amount_payin, writeoff_amount, exchange_rate_payin):
        res = {'value': {}}
        if field in ('amount', 'amount_payin'):
            diff = (amount or 0.0) - (amount_payin or 0.0)
            res['value']['writeoff_amount'] = round(diff, 2)
            res['value']['writeoff_amount_local'] = round(diff * exchange_rate_payin, 2)
        elif field == 'writeoff_amount':
            payin = (amount or 0.0) - (writeoff_amount or 0.0)
            res['value']['amount_payin'] = round(payin, 2)
            res['value']['writeoff_amount_local'] = round(writeoff_amount * exchange_rate_payin, 2)
        return res
      
    @api.multi
    def _unpost_register(self):
        for register in self:
            recs = []
            for line in register.move_ids:
                if line.reconcile_id:
                    recs += [line.reconcile_id]
                if line.reconcile_partial_id:
                    recs += [line.reconcile_partial_id]
            for rec in recs:
                rec.unlink()
            if register.move_id:
                register.move_id.button_cancel()
                register.move_id.unlink()
        return True
     
    @api.multi
    def cancel_register(self):
        self._unpost_register()
        message = "Payment Register <b>cancelled</b>."
        self.message_post(body=message, subtype="payment_register.mt_register")
        res = {
            'state': 'cancel',
            'move_id': False,
        }
        self.write(res)
        return True
 
    # Case bounce check, same as cancel, but status to 'bounce_check' then create new one with reference to the old.
    @api.multi
    def bounce_check(self):
        assert len(self.ids) == 1, 'This option should only be used for a single id at a time.'
        self._unpost_register()
        message = "Payment Register <b>bounced check</b>."
        self.message_post(body=message, subtype="payment_register.mt_register")
        ctx = dict(self._context)
        ctx.update({'bounce_check': True})
        # Create a new document
        new_register_id = self.with_context(ctx).copy({'date': False, 'journal_id': False, 'amount_payin': False})
        res = {
            'state': 'bounce_check',
            'move_id': False,
            'new_register_id': new_register_id.id,
        }
        self.write(res)
        return True
     
    @api.multi
    def cancel_to_draft(self):
        for register_id in self:
            message = "Payment Register <b>set to draft</b>."
            register_id.message_post(body=message, subtype="payment_register.mt_register")
            self.delete_workflow()
            self.create_workflow()
        self.write({'state': 'draft'})
        return True
     
    @api.model
    def _get_company_currency(self, register_id):
        return self.env['payment.register'].browse(register_id).journal_id.company_id.currency_id.id
     
    @api.model
    def _get_current_currency(self, register_id):
        register = self.env['payment.register'].browse(register_id)
        return register.currency_id.id or self._get_company_currency(register.id)
     
    @api.model
    def _sel_context(self, register_id):
        company_currency = self._get_company_currency(register_id)
        current_currency = self._get_current_currency(register_id)
        if current_currency != company_currency:
            context_multi_currency = dict(self._context)
            register_brw = self.env['payment.register'].browse(register_id)
            context_multi_currency.update({'date': register_brw.date})
            return context_multi_currency
        return self._context
     
    @api.model
    def _convert_amount(self, amount, register_id):
        register = self.browse(register_id)
        res = amount
        if register.currency_id.id == register.company_id.currency_id.id:
            # the rate specified on the voucher is for the company currency
            res = register.company_id.currency_id.round((amount * register.exchange_rate))
        else:
            # the rate specified on the voucher is not relevant, we use all the rates in the system
            res = register.currency_id.compute(amount, register.company_id.currency_id)
        return res
     
    @api.model
    def first_move_line_get(self, register_id, move_id, company_currency, current_currency):
        register_brw = self.env['payment.register'].browse(register_id)
        debit = credit = 0.0
        # TODO: is there any other alternative then the voucher type ??
        # ANSWER: We can have payment and receipt "In Advance".
        # TODO: Make this logic available.
        # -for sale, purchase we have but for the payment and receipt we do not have as based on the bank/cash journal we can not know its payment or receipt
        credit = register_brw.paid_amount_in_company_currency
        if debit < 0:
            credit = -debit
            debit = 0.0
        if credit < 0:
            debit = -credit
            credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        # set the first line of the voucher
        move_line = {
            'name': register_brw.name or '/',
            'debit': debit,
            'credit': credit,
            'account_id': register_brw.account_transit_id.id,
            'move_id': move_id,
            'journal_id': register_brw.journal_transit_id.id,
            'period_id': register_brw.period_id.id,
            'partner_id': register_brw.partner_id.id,
            'currency_id': company_currency != current_currency and current_currency or False,
            'amount_currency': company_currency != current_currency and sign * register_brw.amount or 0.0,
            'date': register_brw.date,
            'date_maturity': register_brw.date_due
        }
        return move_line
     
    @api.model
    def account_move_get(self, register_id):
        '''
        This method prepare the creation of the account move related to the given register.
        :param register_id: Id of voucher for which we are creating account_move.
        :return: mapping between fieldname and value of account move to create
        :rtype: dict
        '''
        seq_obj = self.env['ir.sequence']
        register_brw = self.env['payment.register'].browse(register_id)
        if register_brw.number:
            name = register_brw.number
        elif register_brw.journal_id.sequence_id:
            if not register_brw.journal_id.sequence_id.active:
                raise Warning(_('Configuration Error !'), _('Please activate the sequence of selected journal !'))
            name = seq_obj.next_by_id(register_brw.journal_id.sequence_id.id)
        else:
            raise Warning(_('Error!'),
                        _('Please define a sequence on the journal.'))
        if not register_brw.reference:
            ref = name.replace('/', '')
        else:
            ref = register_brw.reference
 
        move = {
            'name': name,
            'journal_id': register_brw.journal_id.id,
            'narration': register_brw.narration,
            'date': register_brw.date,
            'ref': ref,
            'period_id': register_brw.period_id and register_brw.period_id.id or False
        }
        return move

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: