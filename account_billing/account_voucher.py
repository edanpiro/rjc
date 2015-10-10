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

from openerp import models, fields, api, _

class account_voucher(models.Model):
    _inherit = 'account.voucher'
    # 'billing_id': fields.selection(_get_open_billing, "Billing Ref", required=True, size=-1)
    billing_id = fields.Many2one('account.billing', string='Billing Ref', domain=[('state', '=', 'billed'), ('payment_id', '=', False)], readonly=True, states={'draft':[('readonly', False)]})
   
    @api.multi 
    def proforma_voucher(self):
        # Write payment id back to Billing Document
        if self.billing_id:
            self.billing_id.write({'payment_id': self.id})
            self.billing_id.write({'state': 'billed'})
        return super(account_voucher, self).proforma_voucher()
    
    @api.multi
    def cancel_voucher(self):
        # Set payment_id in Billing back to False
        if self.billing_id:
            self.billing_id.write({'payment_id': False})
        return super(account_voucher, self).cancel_voucher()
    
    @api.multi
    def onchange_amount(self, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id):
        res = self.recompute_voucher_lines(partner_id, journal_id, amount, currency_id, ttype, date)
        ctx = dict(self._context)
        ctx.update({'date': date})
        vals = self.onchange_rate(rate, amount, currency_id, payment_rate_currency_id, company_id)
        for key in vals.keys():
            res[key].update(vals[key])
        return res
    
    @api.multi
    def onchange_billing_id(self, partner_id, journal_id, amount, currency_id, ttype, date):
        if not journal_id:
            return {}
        res = self.recompute_voucher_lines(partner_id, journal_id, amount, currency_id, ttype, date)
        vals = self.recompute_payment_rate(res, currency_id, date, ttype, journal_id, amount)
        for key in vals.keys():
            res[key].update(vals[key])
        # TODO: onchange_partner_id() should not returns [pre_line, line_dr_ids, payment_rate...] for type sale, and not 
        # [pre_line, line_cr_ids, payment_rate...] for type purchase.
        # We should definitively split account.voucher object in two and make distinct on_change functions. In the 
        # meanwhile, bellow lines must be there because the fields aren't present in the view, what crashes if the 
        # onchange returns a value for them
        if ttype == 'sale':
            del(res['value']['line_dr_ids'])
            del(res['value']['pre_line'])
            del(res['value']['payment_rate'])
        elif ttype == 'purchase':
            del(res['value']['line_cr_ids'])
            del(res['value']['pre_line'])
            del(res['value']['payment_rate'])
        return res
    
    @api.multi
    def recompute_voucher_lines(self, partner_id, journal_id, price, currency_id, ttype, date):
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
                if currency_id == line.currency_id.id:
                    if line.amount_residual_currency <= 0:
                        return True
                else:
                    if line.amount_residual <= 0:
                        return True
            return False
        
        # testing
        if self._context.get('mode', False) == 'partner':
            return super(account_voucher, self).recompute_voucher_lines(partner_id, journal_id, price, currency_id, ttype, date)
        # -- testing
        
        context_multi_currency = dict(self._context.copy())
        if date:
            context_multi_currency.update({'date': date})

        move_line_pool = self.env['account.move.line']
        partner_pool = self.env['res.partner']
        journal_pool = self.env['account.journal']
        line_pool = self.env['account.voucher.line']
        currency_obj = self.env['res.currency']

        # set default values
        default = {
            'value': {'line_dr_ids': [] , 'line_cr_ids': [] , 'pre_line': False, }
        }

        # drop existing lines
        line_ids = self.ids and line_pool.search([('voucher_id', '=', self.ids[0])]) or False
        if line_ids:
            line_ids.unlink()

        if not partner_id or not journal_id:
            return default

        journal = journal_pool.browse(journal_id)
        partner = partner_pool.browse(partner_id)
        currency_id = currency_id or journal.company_id.currency_id.id
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

        total_credit = 0.0
        total_debit = 0.0
        account_type = 'receivable'
        if ttype == 'payment':
            account_type = 'payable'
            total_debit = price or 0.0
        else:
            total_credit = price or 0.0
            account_type = 'receivable'

        # testing
        if not self._context.get('move_line_ids', False):
            billing_id = self._context.get('billing_id', False)
            if billing_id > 0:
                billing_obj = self.env['account.billing']
                billing = billing_obj.browse(billing_id)
                move_lines = move_line_pool.search([('state', '=', 'valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id),
                                              ('id', 'in', [line.reconcile and line.move_line_id.id or False for line in billing.line_ids])
                                      ])
                ids = move_lines.ids
        # -- testing
            else:
                # For Supplier Payment, also check date.
                invoice_date_condition = []
                if ttype == 'payment':
                    invoice_date_condition = ['|', ('date_maturity', '=', False), ('date_maturity', '<=', date)]
                move_lines = move_line_pool.search([('state', '=', 'valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id)]
                                                        + invoice_date_condition)
                ids = move_lines.ids
        else:
            move_lines = self._context['move_line_ids']
        invoice_id = self._context.get('invoice_id', False)
        company_currency = journal.company_id.currency_id
        move_line_found = False

        # order the lines by most old first
        ids.reverse()
        account_move_lines = move_line_pool.browse(ids)
    

        # compute the total debit/credit and look for a matching open amount or invoice
        for line in account_move_lines:
            if _remove_noise_in_o2m():
                continue

            if invoice_id:
                if line.invoice.id == invoice_id:
                    # if the invoice linked to the voucher line is equal to the invoice_id in context
                    # then we assign the amount on that line, whatever the other voucher lines
                    move_line_found = line.id
                    break
            elif currency_id == company_currency.id:
                # otherwise treatments is the same but with other field names
                if line.amount_residual == price:
                    # if the amount residual is equal the amount voucher, we assign it to that voucher
                    # line, whatever the other voucher lines
                    move_line_found = line.id
                    break
                # otherwise we will split the voucher amount on each line (by most old first)
                total_credit += line.credit or 0.0
                total_debit += line.debit or 0.0
            elif currency_id == line.currency_id.id:
                if line.amount_residual_currency == price:
                    move_line_found = line.id
                    break
                total_credit += line.credit and line.amount_currency or 0.0
                total_debit += line.debit and line.amount_currency or 0.0

        # voucher line creation
        for line in account_move_lines:

            if _remove_noise_in_o2m():
                continue

            if line.currency_id and currency_id == line.currency_id.id:
                amount_original = abs(line.amount_currency)
                amount_unreconciled = abs(line.amount_residual_currency)
            else:
                currency = currency_obj.browse(currency_id)
                amount_original = company_currency.with_context(context_multi_currency).compute(line.credit or line.debit or 0.0, currency)
                amount_unreconciled = company_currency.with_context(context_multi_currency).compute(abs(line.amount_residual), currency)
            line_currency_id = line.currency_id and line.currency_id.id or company_currency.id
            rs = {
                'name':line.move_id.name,
                'type': line.credit and 'dr' or 'cr',
                'move_line_id':line.id,
                'reference':line.invoice.reference,  # testing
                'account_id':line.account_id.id,
                'amount_original': amount_original,
                'amount': (move_line_found == line.id) and min(abs(price), amount_unreconciled) or 0.0,
                'date_original':line.date,
                'date_due':line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'currency_id': line_currency_id,
            }
            # in case a corresponding move_line hasn't been found, we now try to assign the voucher amount
            # on existing invoices: we split voucher amount by most old first, but only for lines in the same currency
            if not move_line_found:
                if currency_id == line_currency_id:
                    if line.credit:
                        amount = min(amount_unreconciled, abs(total_debit))
                        rs['amount'] = amount
                        total_debit -= amount
                    else:
                        amount = min(amount_unreconciled, abs(total_credit))
                        rs['amount'] = amount
                        total_credit -= amount

            if rs['amount_unreconciled'] == rs['amount']:
                rs['reconcile'] = True

            if rs['type'] == 'cr':
                default['value']['line_cr_ids'].append(rs)
            else:
                default['value']['line_dr_ids'].append(rs)

            if ttype == 'payment' and len(default['value']['line_cr_ids']) > 0:
                default['value']['pre_line'] = 1
            elif ttype == 'receipt' and len(default['value']['line_dr_ids']) > 0:
                default['value']['pre_line'] = 1
            default['value']['writeoff_amount'] = self._compute_writeoff_amount(default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, ttype)
        return default

class account_voucher_line(models.Model):
    _inherit = 'account.voucher.line'

    reference = fields.Char(string='Invoice Reference', help="The partner reference of this invoice.")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: