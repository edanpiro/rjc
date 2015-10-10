# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#     Copyright (C) 2012 Cubic ERP - Teradata SAC (<http://cubicerp.com>).
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
import time

class account_transfer(models.Model):
    
    @api.model
    def _get_balance(self, src_journal, dst_journal, company):
        src_balance = dst_balance = 0.0
        # import pdb; pdb.set_trace()
        if src_journal.default_credit_account_id.id == src_journal.default_debit_account_id.id:
            if not src_journal.currency or company.currency_id.id == src_journal.currency.id:
                src_balance = src_journal.default_credit_account_id.balance
            else:
                src_balance = src_journal.default_credit_account_id.foreign_balance
        else:
            if not src_journal.currency or company.currency_id.id == src_journal.currency.id:
                src_balance = src_journal.default_debit_account_id.balance - src_journal.default_credit_account_id.balance
            else:
                src_balance = src_journal.default_debit_account_id.foreign_balance - src_journal.default_credit_account_id.foreign_balance
        if dst_journal.default_credit_account_id.id == dst_journal.default_debit_account_id.id:
            if not dst_journal.currency or company.currency_id.id == dst_journal.currency.id:
                dst_balance = dst_journal.default_credit_account_id.balance
            else:
                dst_balance = dst_journal.default_credit_account_id.foreign_balance
        else:
            if not dst_journal.currency or company.currency_id.id == dst_journal.currency.id:
                dst_balance = dst_journal.default_debit_account_id.balance - dst_journal.default_credit_account_id.balance
            else:
                dst_balance = dst_journal.default_debit_account_id.foreign_balance - dst_journal.default_credit_account_id.foreign_balance
        return (src_balance, dst_balance)
        
    @api.one
    @api.depends('dst_journal_id', 'src_journal_id', 'company_id')
    def _balance(self):
        src_balance, dst_balance = self._get_balance(self.src_journal_id, self.dst_journal_id, self.company_id)
        exchange = False
        if self.dst_journal_id.currency.id != self.src_journal_id.currency.id:
            exchange = True
        self.src_balance = src_balance
        self.dst_balance = dst_balance
        self.exchange = exchange
        self.exchange_inv = (self.exchange_rate and 1.0 / self.exchange_rate or 0.0)

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ]

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id)
    name = fields.Char(string='Number', required=True, readonly=True, states={'draft': [('readonly', False)]}, default='/')
    date = fields.Date(string='Date', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=time.strftime('%Y-%m-%d'))
    origin = fields.Char(string='Origin', readonly=True, states={'draft': [('readonly', False)]}, help="Origin Document")
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True, states={'draft': [('readonly', False)]})
    voucher_ids = fields.One2many('account.voucher', 'transfer_id', string='Payments', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, copy=False)
    src_journal_id = fields.Many2one('account.journal', string='Source Journal', required=True, domain=[('type', 'in', ['cash', 'bank'])], select=True, readonly=True, states={'draft': [('readonly', False)]})
    src_partner_id = fields.Many2one('res.partner', string='Source Partner', select=True)
    src_balance = fields.Float(compute='_balance', digits_compute=dp.get_precision('Account'), string='Current Source Balance', readonly=True, help="Include all account moves in draft and confirmed state")
    src_amount = fields.Float(string='Source Amount', required=True, readonly=True, states={'draft': [('readonly', False)]})
    src_have_partner = fields.Boolean(related='src_journal_id.have_partner', string='Have Partner', readonly=True)
    dst_journal_id = fields.Many2one('account.journal', string='Destinity Journal', required=True, domain=[('type', 'in', ['cash', 'bank'])], select=True, readonly=True, states={'draft': [('readonly', False)]})
    dst_partner_id = fields.Many2one('res.partner', string='Destinity Partner', select=True)
    dst_balance = fields.Float(compute='_balance', digits_compute=dp.get_precision('Account'), string='Current Destinity Balance', readonly=True, help="Include all account moves in draft and confirmed state")
    dst_amount = fields.Float(string='Destinity Amount', required=True, readonly=True, states={'draft': [('readonly', False)]})
    dst_have_partner = fields.Boolean(related='dst_journal_id.have_partner', string='Have Partner', readonly=True)
    exchange_rate = fields.Float(string='Exchange Rate', digits_compute=dp.get_precision('Exchange'), readonly=True, states={'draft': [('readonly', False)]}, default=1.0)
    exchange = fields.Boolean(compute='_balance', string='Have Exchange', readonly=True)
    exchange_inv = fields.Float(compute='_balance', string='1 / Exchange Rate', digits_compute=dp.get_precision('Exchange'), readonly=True, default=1.0)
    adjust_move = fields.Many2one('account.move', string='Adjust Move', readonly=True, help="Adjust move usually by difference in the money exchange")
    state = fields.Selection(selection=STATE_SELECTION, string='State', readonly=True, default='draft')
    
    _sql_constraints = [('name_unique', 'unique(company_id,name)', _('The number must be unique!'))]
    _name = 'account.transfer'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Account Cash and Bank Transfer'
    _order = 'name desc'
    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get('account.transfer') or '/'
        return super(account_transfer, self).create(vals)
    
    @api.multi
    def unlink(self):
        for trans in self:
            if trans.state not in ('draft'):
                raise Warning(_('User Error!'), _('You cannot delete a not draft transfer "%s"') % trans.name)
        return super(account_transfer, self).unlink()
    
    @api.multi
    def copy(self, defaults):
        defaults['name'] = self.env['ir.sequence'].get('account.transfer')
        defaults['voucher_ids'] = []
        return super(account_transfer, self).copy(defaults)

    @api.multi    
    def onchange_amount(self, field, src_amount, dst_amount, exchange_rate):
        res = {'value': {}}
        if field == 'src_amount':
            res['value']['src_amount'] = src_amount
            res['value']['dst_amount'] = round(src_amount * exchange_rate, 2)  # Round to avoid infinite looping
            res['value']['exchange_rate'] = exchange_rate
            res['value']['exchange_inv'] = exchange_rate and 1.0 / exchange_rate or 0.0
        elif field == 'dst_amount':
            res['value']['src_amount'] = round(exchange_rate and dst_amount / exchange_rate or 0.0, 2)  # Round to avoid infinite looping
            res['value']['dst_amount'] = dst_amount
            res['value']['exchange_rate'] = exchange_rate
            res['value']['exchange_inv'] = exchange_rate and 1.0 / exchange_rate or 0.0
        elif field == 'exchange_rate':
            res['value']['src_amount'] = src_amount
            res['value']['dst_amount'] = round(src_amount * exchange_rate, 2)  # Round to avoid infinite looping
            res['value']['exchange_rate'] = exchange_rate
            res['value']['exchange_inv'] = exchange_rate and 1.0 / exchange_rate or 0.0
        return res
    
    @api.onchange('src_journal_id', 'dst_journal_id')    
    def onchange_journal(self):
        res = {'value': {}}
        if not(self.src_journal_id and self.dst_journal_id):
            return res
        self.src_balance, self.dst_balance = self._get_balance(self.src_journal_id, self.dst_journal_id, self.src_journal_id.company_id)
        self.exchange = (self.src_journal_id.currency.id != self.dst_journal_id.currency.id)
        self.src_have_partner, self.dst_have_partner = self.src_journal_id.have_partner, self.dst_journal_id.have_partner
        self.exchange_rate = self.exchange_rate
        if self.exchange:
            self.exchange_rate = (self.src_journal_id.currency and self.src_journal_id.currency.rate or self.src_journal_id.company_id.currency_id.rate) and ((self.dst_journal_id.currency and self.dst_journal_id.currency.rate or self.dst_journal_id.company_id.currency_id.rate) / (self.src_journal_id.currency and self.src_journal_id.currency.rate or self.src_journal.company_id.currency_id.rate)) or 0.0
        else:
            self.exchange_rate = 1.0
        self.exchange_inv = self.exchange_rate and (1.0 / self.exchange_rate) or 0.0
        self.dst_amount = self.exchange_rate * self.src_amount
        return res
    
    @api.multi
    def action_confirm(self):
        voucher_obj = self.env['account.voucher']
        for trans in self:
            sval = {}
            dval = {}
            sval['date'] = trans.date
            dval['date'] = trans.date
            sval['transfer_id'] = trans.id
            dval['transfer_id'] = trans.id
            sval['type'] = 'transfer'
            dval['type'] = 'transfer'
            sval['company_id'] = trans.company_id.id
            dval['company_id'] = trans.company_id.id
            sval['reference'] = trans.name + (trans.origin and (' - ' + trans.origin) or '')
            dval['reference'] = trans.name + (trans.origin and (' - ' + trans.origin) or '')
            sval['line_ids'] = [(0, 0, {})]
            dval['line_ids'] = [(0, 0, {})]
            sval['line_ids'][0][2]['account_analytic_id'] = trans.account_analytic_id and trans.account_analytic_id.id or 0
            dval['line_ids'][0][2]['account_analytic_id'] = trans.account_analytic_id and trans.account_analytic_id.id or 0
            sval['line_ids'][0][2]['name'] = trans.origin
            dval['line_ids'][0][2]['name'] = trans.origin
            sval['journal_id'] = trans.src_journal_id.id
            dval['journal_id'] = trans.dst_journal_id.id
            sval['account_id'] = trans.src_journal_id.default_credit_account_id.id
            dval['account_id'] = trans.dst_journal_id.default_debit_account_id.id
            sval['payment_rate'] = trans.src_journal_id.currency.id and trans.company_id.currency_id.id != trans.src_journal_id.currency.id and trans.exchange_rate or 1.0
            dval['payment_rate'] = trans.dst_journal_id.currency.id and trans.company_id.currency_id.id != trans.dst_journal_id.currency.id and trans.exchange_inv or 1.0
            sval['payment_rate_currency_id'] = trans.dst_journal_id.currency.id or trans.company_id.currency_id.id
            dval['payment_rate_currency_id'] = trans.src_journal_id.currency.id or trans.company_id.currency_id.id
            # import pdb; pdb.set_trace()
            sval['line_ids'][0][2]['amount'] = sval['amount'] = trans.src_amount
            dval['line_ids'][0][2]['amount'] = dval['amount'] = trans.dst_amount
            sval['line_ids'][0][2]['type'] = 'dr'
            dval['line_ids'][0][2]['type'] = 'cr'
            sval['line_ids'][0][2]['account_id'] = trans.dst_journal_id.default_debit_account_id.id
            if trans.src_partner_id.id ^ trans.dst_partner_id.id:
                sval['partner_id'] = trans.src_have_partner and trans.src_partner_id.id or trans.dst_partner_id.id
            else:
                sval['partner_id'] = trans.src_have_partner and trans.src_partner_id.id or trans.company_id.partner_id.id
                dval['partner_id'] = trans.dst_have_partner and trans.dst_partner_id.id or trans.company_id.partner_id.id
                sval['line_ids'][0][2]['account_id'] = dval['line_ids'][0][2]['account_id'] = trans.src_journal_id.account_transit.id
                # import pdb; pdb.set_trace()
                voucher_obj.create(dval)
            voucher_obj.create(sval)
        return self.write({'state': 'confirm'})
    
    @api.multi
    def action_done(self):
        move_obj = self.env['account.move']
        for trans in self:
            paid_amount = []
            # import pdb; pdb.set_trace()
            for voucher in trans.voucher_ids:
                if voucher.state == 'draft':
                    voucher.proforma_voucher()
                sign = (voucher.journal_id.id == trans.src_journal_id.id) and 1 or -1
                paid_amount.append(sign * voucher.paid_amount_in_company_currency)
                # paid_amount.append(sign * voucher.paid_amount_in_company_currency)
            sum_amount = sum(paid_amount)
            if len(paid_amount) > 1 and sum_amount != 0.0:
                periods = self.env['account.period'].find()
                move = {}
                move['journal_id'] = trans.dst_journal_id.id
                move['period_id'] = periods and periods[0] or False
                move['ref'] = trans.name + str(trans.origin and (' - ' + trans.origin) or '')
                move['date'] = trans.date
                move['line_id'] = [(0, 0, {}), (0, 0, {})]
                move['line_id'][0][2]['name'] = trans.name
                move['line_id'][1][2]['name'] = trans.name
                if sum_amount > 0:
                    move['line_id'][0][2]['account_id'] = trans.dst_journal_id.default_debit_account_id.id
                    move['line_id'][1][2]['account_id'] = trans.src_journal_id.account_transit.id  # trans.company_id.income_currency_exchange_account_id.id
                    move['line_id'][0][2]['debit'] = sum_amount
                    move['line_id'][1][2]['credit'] = sum_amount
                else:
                    move['line_id'][0][2]['account_id'] = trans.dst_journal_id.default_credit_account_id.id
                    move['line_id'][1][2]['account_id'] = trans.src_journal_id.account_transit.id  # trans.company_id.expense_currency_exchange_account_id.id
                    move['line_id'][1][2]['debit'] = -1 * sum_amount
                    move['line_id'][0][2]['credit'] = -1 * sum_amount
                move_id = move_obj.create(move)
                trans.write({'adjust_move': move_id.id})
        return self.write({'state': 'done'})
    
    @api.multi
    def action_cancel(self):
        # import pdb; pdb.set_trace()
        for trans in self:
            for voucher in self.voucher_ids:
                voucher.unlink()
            trans.adjust_move and trans.adjust_move.unlink()
        return self.write({'state': 'cancel'})

