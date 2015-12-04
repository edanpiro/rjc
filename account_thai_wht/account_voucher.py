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
import time

class common_voucher(object):
    
    @api.model
    def _to_invoice_currency(self, invoice, journal, amount):
        ctx = dict(self._context)
        inv_currency_id = invoice.currency_id
        cur_currency_id = journal.currency and journal.currency or journal.company_id.currency_id
        ctx.update({'date': invoice.date_invoice})
        amount = inv_currency_id.with_context(ctx).compute(float(amount), cur_currency_id)
        return amount
    
    @api.model
    def _to_voucher_currency(self, invoice, journal, amount):
        ctx = dict(self._context)
        inv_currency_id = invoice.currency_id
        cur_currency_id = journal.currency and journal.currency or journal.company_id.currency_id
        if inv_currency_id != cur_currency_id:
            amount = inv_currency_id.with_context(ctx).compute(float(amount), cur_currency_id)
        return amount

class account_voucher(common_voucher, models.Model):
    _inherit = 'account.voucher'
    
    @api.model
    def _compute_writeoff_amount(self, line_dr_ids, line_cr_ids, amount, type):
        debit = credit = 0.0
        sign = type == 'payment' and -1 or 1
        for l in line_dr_ids:
	    if isinstance(l, dict):
	       debit += l['amount'] + l.get('amount_wht', 0.0)  # Add WHT
        for l in line_cr_ids:
	    if isinstance(l, dict):
	       credit += l['amount'] + l.get('amount_wht', 0.0)  # Add WHT
        return amount - sign * (credit - debit)

    # This is a complete overwrite method
    @api.one
    @api.depends('line_dr_ids', 'line_cr_ids')
    def _get_writeoff_amount(self):
        if not self.ids:
            return {}
        debit = credit = 0.0
        sign = self.type == 'payment' and -1 or 1
        for l in self.line_dr_ids:
            debit += l.amount + l.amount_wht  # Add WHT
        for l in self.line_cr_ids:
            credit += l.amount + l.amount_wht  # Add WHT
        currency = self.currency_id or self.company_id.currency_id
        self.writeoff_amount = currency.round(self.amount - sign * (credit - debit))

    # Note: This method is not exactly the same as the line's one.
    @api.model
    def _get_amount_wht_ex(self, partner_id, move_line_id, amount_original, original_wht_amt, amount, advance_and_discount={}):
        tax_obj = self.env['account.tax']
        partner_obj = self.env['res.partner']
        move_line_obj = self.env['account.move.line']
        
        partner = partner_obj.browse(partner_id)
        move_line = move_line_obj.browse(move_line_id)
        amount_wht = 0.0

        if move_line.invoice:
            invoice = move_line.invoice
            add_disc = advance = deposit = 0.0
            if advance_and_discount:
                add_disc = advance_and_discount['add_disc']
                advance = advance_and_discount['advance']
                deposit = advance_and_discount['deposit']

            for line in invoice.invoice_line:
                revised_price = line.price_unit * (1 - (line.discount or 0.0) / 100.0) * (1 - (add_disc or 0.0) / 100.0) * (1 - (advance or 0.0) / 100.0) * (1 - (deposit or 0.0) / 100.0)
                # Only WHT
                is_wht = True in [x.is_wht for x in line.invoice_line_tax_id] or False
                if is_wht:
                    for tax in line.invoice_line_tax_id.compute_all(
                                                   revised_price * ((amount_original - original_wht_amt) and amount / (amount_original - original_wht_amt) or 0.0),
                                                   line.quantity, line.product_id, partner, force_excluded=False)['taxes']:
                        if tax_obj.browse(tax['id']).is_wht:
                            # Check Threshold first
                            base = revised_price * line.quantity
                            if abs(base) and abs(base) < tax_obj.browse(tax['id']).threshold_wht:
                                continue
                            amount_wht += tax['amount']
            # Convert to voucher currency
            amount_wht = self._to_voucher_currency(invoice, move_line.journal_id, amount_wht)

        return float(amount), float(amount_wht)

    writeoff_amount = fields.Float(compute='_get_writeoff_amount', string='Difference Amount', readonly=True, help="Computed as the difference between the amount stated in the voucher and the sum of allocation on the voucher lines.")
    tax_line = fields.One2many('account.voucher.tax', 'voucher_id', 'Tax Lines')
    
    @api.multi
    def recompute_voucher_lines(self, partner_id, journal_id, price, currency_id, ttype, date):
        res = self.recompute_voucher_lines_ex(partner_id, journal_id, price, currency_id, ttype, date, advance_and_discount={})
        return res

    # The original recompute_voucher_lines() do not aware of withholding.
    # Here we will re-adjust it. As such, the amount allocation will be reduced and carry to the next lines.
    @api.multi
    def recompute_voucher_lines_ex(self, partner_id, journal_id, price, currency_id, ttype, date, advance_and_discount={}):
        res = super(account_voucher, self).recompute_voucher_lines(partner_id, journal_id, price, currency_id, ttype, date)
        line_cr_ids = res['value']['line_cr_ids']
        line_dr_ids = res['value']['line_dr_ids']
        sign = 0
        move_line_obj = self.env['account.move.line']
        remain_amount = float(price)

        if ttype == 'payment':
            lines = line_cr_ids + line_dr_ids
        else:
            lines = line_dr_ids + line_cr_ids

	for line in lines:
	    if not isinstance(line, dict):
                continue
            amount, amount_wht = 0.0, 0.0
            adv_disc = {}
            if advance_and_discount:
                move_line = move_line_obj.browse(line['move_line_id'])
                invoice = move_line.invoice
                adv_disc = advance_and_discount[invoice.id]

            # Test to get full wht first
            original_amount, original_wht_amt = self.env['account.voucher.line']._get_amount_wht(partner_id, line['move_line_id'], line['amount_original'], line['amount_original'], adv_disc)
            # Full amount to reconcile
            amount_alloc = original_amount > 0.0 and (line['amount_unreconciled'] * (original_amount - original_wht_amt) / original_amount) or 0.0
            # Allocations Amount
            if ttype == 'payment':  # Supplier Payment
                if line['type'] == 'cr':  # always full allocation.
                    sign = 1
                    amount_alloc = amount_alloc
                else:  # cr, spend the remainings
                    sign = -1
                    if remain_amount == 0.0:
                        amount_alloc = 0.0
                    else:
                        amount_alloc = amount_alloc > remain_amount and remain_amount or amount_alloc
            else:  # Customer Payment
                if line['type'] == 'dr':  # always full allocation.
                    sign = 1
                    amount_alloc = amount_alloc
                else:  # cr, spend the remainings
                    sign = -1
                    if remain_amount == 0.0:
                        amount_alloc = 0.0
                    else:
                        amount_alloc = amount_alloc > remain_amount and remain_amount or amount_alloc

            # ** Calculate withholding amount **
            if amount_alloc:
                amount, amount_wht = self._get_amount_wht_ex(partner_id, line['move_line_id'], line['amount_original'], original_wht_amt, amount_alloc, advance_and_discount)
            # Adjust remaining
            remain_amount = remain_amount + (sign * amount_alloc)
            line['amount'] = amount + amount_wht
            line['amount_wht'] = -amount_wht
            line['reconcile'] = line['amount'] == line['amount_unreconciled']
        return res
    
    @api.multi
    def button_reset_taxes(self):
        ctx = dict(self._context)
        avt_obj = self.env['account.voucher.tax']
        for voucher in self:
            # Only update if voucher state is not "posted"
            if voucher.state == 'posted':
                continue
            self._cr.execute("DELETE FROM account_voucher_tax WHERE voucher_id=%s AND manual is False", (self.id,))
            partner = voucher.partner_id
            if partner.lang:
                ctx.update({'lang': partner.lang})
            for tax in avt_obj.with_context(ctx).compute(self.id).values():
                avt_obj.create(tax)
        # Update the stored value (fields.function), so we write to trigger recompute
        # self.pool.get('account.voucher').write(cr, uid, ids, {'line_ids':[]}, context=ctx)
        return True
    #  automatic compute tax then save
    @api.multi
    def write(self, vals):
        res = super(account_voucher, self).write(vals)
        # When editing only tax amount, do not reset tax
        to_update = True
        if vals.get('tax_line', False):
            for tax_line in vals.get('tax_line'):
                if tax_line[0] == 1 and 'amount' in tax_line[2]:  # 1 = update
                    to_update = False
        if to_update:
            self.button_reset_taxes()
        return res

    # A complete overwrite method++
    @api.multi
    def action_move_line_create(self):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        move_pool = self.env['account.move']
        move_line_pool = self.env['account.move.line']
        for voucher in self:
            if voucher.move_id:
                continue
            company_currency = self._get_company_currency(voucher.id)
            current_currency = self._get_current_currency(voucher.id)
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(voucher.id)
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = dict(self._context.copy())
            ctx.update({'date': voucher.date})
            # Create the account move record.
            move_id = move_pool.create(self.account_move_get(voucher.id))
            # Get the name of the account_move just created
            name = move_id.name
            # Create the first line of the voucher
            move_line_brw = move_line_pool.create(self.first_move_line_get(voucher.id, move_id.id, company_currency, current_currency))
            line_total = move_line_brw.debit - move_line_brw.credit
            rec_list_ids = []
            rec_wht_ids = []
            net_tax = 0.0
            if voucher.type == 'sale':
                line_total = line_total - self.with_context(ctx)._convert_amount(voucher.tax_amount, voucher.id)
            elif voucher.type == 'purchase':
                line_total = line_total + self.with_context(ctx)._convert_amount(voucher.tax_amount, voucher.id)

            # testing - Thai Accounting
            # If voucher.type = receipt or payment, it is possible to have tax.
            elif voucher.type in ('receipt', 'payment'):  # Create dr/cr for taxes, then remove the net amount from line_total
                net_tax, rec_wht_ids = self.voucher_move_line_tax_create(voucher, move_id.id, company_currency, current_currency)
#                 move_line_pool.write(cr, uid, [move_line_id], {'debit': move_line_brw.debit and (move_line_brw.debit - net_tax) or 0.0,
#                                                                'credit': move_line_brw.credit and (move_line_brw.credit + net_tax) or 0.0,})
            # -- testing

            # Create one move line per voucher line where amount is not 0.0
            line_total, rec_list_ids = self.voucher_move_line_create(voucher.id, line_total, move_id.id, company_currency, current_currency)

            # testing - Thai Accounting, make sure to adjust with tax before making writeoff.
            line_total = line_total + net_tax
            # -- testing

            # Create the writeoff line if needed
            ml_writeoff = self.writeoff_move_line_get(voucher.id, line_total, move_id.id, name, company_currency, current_currency)
            if ml_writeoff:
                move_line_pool.create(ml_writeoff)
            # We post the voucher.
            voucher.write({
                'move_id': move_id.id,
                'state': 'posted',
                'number': name,
            })
            if voucher.journal_id.entry_posted:
                move_id.post()
            # We automatically reconcile the account move lines.
            reconcile = False
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    recs = move_line_pool.browse(rec_ids)
                    reconcile = recs.reconcile_partial(rec_ids, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)
        return True

    # testing -- New Method for account.voucher.tax
    @api.model
    def voucher_move_line_tax_create(self, voucher, move_id, company_currency, current_currency):
        move_line_obj = self.env['account.move.line']
        avt_obj = self.env['account.voucher.tax']
        # one move line per tax line
        vtml = avt_obj.move_line_get(voucher.id)
        # create gain/loss from currency between invoice and voucher
        vtml = self.compute_tax_currency_gain(voucher, vtml)
        # create one move line for the total and possibly adjust the other lines amount
        net_tax_currency, vtml = self.compute_net_tax(voucher, company_currency, vtml)
        # Create move line,
        rec_ids = []
        for ml in vtml:
            ml.update({'move_id': move_id})
            new_id = move_line_obj.create(ml)
            rec_ids.append(new_id)
        return net_tax_currency, rec_ids

    # testing -- New Method to compute the net tax (cr/dr)
    @api.model
    def compute_net_tax(self, voucher, company_currency, voucher_tax_move_lines):
        total = 0
        total_currency = 0
        cur_obj = self.env['res.currency']
        current_currency = self._get_current_currency(voucher.id)
        for i in voucher_tax_move_lines:
            if current_currency != company_currency:
                ctx = dict(self._context)
                ctx.update({'date': voucher.date or time.strftime('%Y-%m-%d')})
                i['currency_id'] = current_currency
                i['amount_currency'] = i['price']
                i['price'] = cur_obj.compute(current_currency, company_currency, i['price'])
            else:
                i['amount_currency'] = False
                i['currency_id'] = False

            debit = credit = 0.0

            if voucher.type == 'payment':
                debit = i['amount_currency'] or i['price']
                total += i['price']
                total_currency += i['amount_currency'] or i['price']
            else:
                credit = i['amount_currency'] or i['price']
                total -= i['price']
                total_currency -= i['amount_currency'] or i['price']
                i['price'] = -i['price']

            if debit < 0: credit = -debit; debit = 0.0
            if credit < 0: debit = -credit; credit = 0.0
            sign = debit - credit < 0 and -1 or 1
            # 'journal_id': voucher_brw.journal_id.id,
            i['period_id'] = voucher.period_id.id
            i['partner_id'] = voucher.partner_id.id
            i['date'] = voucher.date
            i['date_maturity'] = voucher.date_due
            i['debit'] = debit
            i['credit'] = credit

        return total_currency, voucher_tax_move_lines

    # testing -- New Method to add gain loss from currency for tax
    @api.model
    def compute_tax_currency_gain(self, voucher, voucher_tax_move_lines):
        for i in voucher_tax_move_lines:
            if 'tax_currency_gain' in i and i['tax_currency_gain']:
                debit = credit = 0.0
                if voucher.type == 'payment':
                    debit = i['tax_currency_gain']
                else:
                    credit = i['tax_currency_gain']
                if debit < 0: credit = -debit; debit = 0.0
                if credit < 0: debit = -credit; credit = 0.0
                gain_account_id = 0
                loss_account_id = 0
                if voucher.company_id.income_currency_exchange_account_id and voucher.company_id.expense_currency_exchange_account_id:
                    gain_account_id = voucher.company_id.income_currency_exchange_account_id.id
                    loss_account_id = voucher.company_id.expense_currency_exchange_account_id.id
                else:
                    raise Warning(_('Error!'),
                        _('There is no gain/loss accounting defined in the system!'))
                if debit > 0.0 or credit > 0.0:
                    sign = debit - credit < 0 and -1 or 1
                    voucher_tax_move_lines.append({
                        'type': 'tax',
                        'name': _('Gain/Loss from Suspended VAT'),
                        'quantity': 1,
                        'price': sign * (credit or -debit),
                        'account_id': credit and gain_account_id or loss_account_id
                    })

        return voucher_tax_move_lines

class account_voucher_line(common_voucher, models.Model):
    _inherit = 'account.voucher.line'

    amount_wht = fields.Float(string='WHT', digits_compute=dp.get_precision('Account'))
    
    @api.model
    def _get_amount_wht(self, partner_id, move_line_id, amount_original, amount, advance_and_discount={}):
        tax_obj = self.env['account.tax']
        partner_obj = self.env['res.partner']
        move_line_obj = self.env['account.move.line']
        partner = partner_obj.browse(partner_id)
        move_line = move_line_obj.browse(move_line_id)
        amount_wht = 0.0

        if move_line.invoice:
            invoice = move_line.invoice
            add_disc = advance = deposit = 0.0
            if advance_and_discount:
                add_disc = advance_and_discount['add_disc']
                advance = advance_and_discount['advance']
                deposit = advance_and_discount['deposit']

            for line in invoice.invoice_line:
                revised_price = line.price_unit * (1 - (line.discount or 0.0) / 100.0) * (1 - (add_disc or 0.0) / 100.0) * (1 - (advance or 0.0) / 100.0) * (1 - (deposit or 0.0) / 100.0)
                # Only WHT
                is_wht = True in [x.is_wht for x in line.invoice_line_tax_id] or False
                if is_wht:
                    for tax in line.invoice_line_tax_id.compute_all(
                            float(revised_price) * (float(amount_original) and (float(amount) / float(amount_original)) or 0.0),
                            line.quantity, line.product_id, partner, force_excluded=False)['taxes']:
                        if tax_obj.browse(tax['id']).is_wht:
                            amount_wht += tax['amount']

            # Change to currency at invoicing time.
            amount_wht = self._to_voucher_currency(invoice, move_line.journal_id, amount_wht)

        return float(amount), float(amount_wht)
    
    @api.multi
    def onchange_amount(self, partner_id, move_line_id, amount_original, amount, amount_unreconciled):
        vals = {}
        prec = self.env['decimal.precision'].precision_get('Account')
        amount, amount_wht = self._get_amount_wht(partner_id, move_line_id, amount_original, amount, advance_and_discount={})
        vals['amount_wht'] = -round(amount_wht, prec)
        vals['reconcile'] = (round(amount) == round(amount_unreconciled))
        return {'value': vals}
    
    @api.multi
    def onchange_reconcile(self, partner_id, move_line_id, amount_original, reconcile, amount, amount_unreconciled):
        vals = {}
        prec = self.env['decimal.precision'].precision_get('Account')
        if reconcile:
            amount = amount_unreconciled
            amount, amount_wht = self._get_amount_wht(partner_id, move_line_id, amount_original, amount, advance_and_discount={})
            vals['amount_wht'] = -round(amount_wht, prec)
            vals['amount'] = round(amount, prec)
        return {'value': vals}

# testing -- New class
class account_voucher_tax(common_voucher, models.Model):
    _name = "account.voucher.tax"
    _description = "Voucher Tax"
    
    @api.one
    @api.depends('tax_amount', 'base_amount', 'amount', 'base')
    def _count_factor(self):
        self.factor_base = 1.0
        self.factor_tax = 1.0
        if self.amount <> 0.0:
            factor_tax = self.tax_amount / self.amount
            self.factor_tax = factor_tax

        if self.base <> 0.0:
            factor_base = self.base_amount / self.base
            self.factor_base = factor_base

    voucher_id = fields.Many2one('account.voucher', string='Voucher Line', ondelete='cascade', select=True)
    tax_id = fields.Many2one('account.tax', string='Tax')
    name = fields.Char(string='Tax Description', required=True)
    name2 = fields.Char(string='Tax Description 2', required=False)
    account_id = fields.Many2one('account.account', string='Tax Account', required=True, domain=[('type', '<>', 'view'), ('type', '<>', 'income'), ('type', '<>', 'closed')])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    base = fields.Float(string='Base', digits_compute=dp.get_precision('Account'))
    amount = fields.Float(string='Amount', digits_compute=dp.get_precision('Account'))
    tax_currency_gain = fields.Float(string='Currency Gain', digits_compute=dp.get_precision('Account'))
    manual = fields.Boolean(string='Manual', default=1)
    sequence = fields.Integer(string='Sequence', help="Gives the sequence order when displaying a list of voucher tax.")
    base_code_id = fields.Many2one('account.tax.code', string='Base Code', help="The account basis of the tax declaration.")
    base_amount = fields.Float('Base Code Amount', digits_compute=dp.get_precision('Account'), default=0.0)
    tax_code_id = fields.Many2one('account.tax.code', string='Tax Code', help="The tax basis of the tax declaration.")
    tax_amount = fields.Float(string='Tax Code Amount', digits_compute=dp.get_precision('Account'), default=0.0)
    company_id = fields.Many2one(related='account_id.company_id', string='Company', store=True, readonly=True)
    factor_base = fields.Float(compute='_count_factor', string='Multipication factor for Base code', multi="all")
    factor_tax = fields.Float(compute='_count_factor', string='Multipication factor Tax code', multi="all")

    _order = 'sequence'
    
    @api.model
    def compute(self, voucher_id):
        tax_grouped = self.compute_ex(voucher_id, advance_and_discount={})
        return tax_grouped
    
    @api.model
    def compute_ex(self, voucher_id, advance_and_discount={}):
        tax_grouped = {}
        tax_obj = self.env['account.tax']
        cur_obj = self.env['res.currency']
        voucher = self.env['account.voucher'].browse(voucher_id)
        cur = voucher.currency_id or voucher.journal_id.company_id.currency_id
        company_currency = voucher.company_id.currency_id
        # Special case for account_voucher_taxinv, get only suspended tax, based on inovice
        # testing: change to use exactly as tax table
        is_taxinv = 'is_taxinv' in self._context and self._context['is_taxinv'] or False
        # --
        for voucher_line in voucher.line_ids:
            line_sign = 1
            if voucher.type in ('sale', 'receipt'):
                line_sign = voucher_line.type == 'cr' and 1 or -1
            elif voucher.type in ('purchase', 'payment'):
                line_sign = voucher_line.type == 'dr' and 1 or -1
            # Each voucher line is equal to an invoice, we will need to go through all of them.
            if voucher_line.move_line_id.invoice:
                invoice = voucher_line.move_line_id.invoice
                journal = voucher_line.voucher_id.journal_id
                payment_ratio = voucher_line.amount_original == 0.0 and 0.0 or (voucher_line.amount / (voucher_line.amount_original or 1))
                # Retrieve Additional Discount, Advance and Deposit in percent.
                add_disc = advance = deposit = 0.0
                if advance_and_discount:
                    add_disc = advance_and_discount[invoice.id]['add_disc']
                    advance = advance_and_discount[invoice.id]['advance']
                    deposit = advance_and_discount[invoice.id]['deposit']
                for line in voucher_line.move_line_id.invoice.invoice_line:
                    # Each invoice line, calculate tax
                    revised_price = line.price_unit * (1 - (line.discount or 0.0) / 100.0) * (1 - (add_disc or 0.0) / 100.0) * (1 - (advance or 0.0) / 100.0) * (1 - (deposit or 0.0) / 100.0)
                    for tax in line.invoice_line_tax_id.compute_all(revised_price, line.quantity, line.product_id, voucher.partner_id, force_excluded=False)['taxes']:
                        # For Normal
                        
                        ctx = dict(self._context or {})
                        ctx.update({'date': invoice.date_invoice or time.strftime('%Y-%m-%d')})
                
                        val = {}
                        val['voucher_id'] = voucher.id
                        val['tax_id'] = tax['id']
                        val['name'] = tax['name']
                        val['amount'] = self._to_voucher_currency(invoice, journal, \
                                            tax['amount'] * payment_ratio * line_sign, \
                                            )
                        val['manual'] = False
                        val['sequence'] = tax['sequence']
                        val['base'] = self._to_voucher_currency(invoice, journal, \
                                            cur.round(tax['price_unit'] * line.quantity) * payment_ratio * line_sign, \
                                            )
                        # For Suspend
                        vals = {}
                        vals['voucher_id'] = voucher.id
                        vals['tax_id'] = tax['id']
                        vals['name'] = tax['name']
                        vals['amount'] = self._to_invoice_currency(invoice, journal, \
                                            - tax['amount'] * payment_ratio * line_sign, \
                                            )
                        vals['manual'] = False
                        vals['sequence'] = tax['sequence']
                        vals['base'] = self._to_invoice_currency(invoice, journal, \
                                            - cur.round(tax['price_unit'] * line.quantity) * payment_ratio * line_sign, \
                                            )

                        # Register Currency Gain for Normal
                        val['tax_currency_gain'] = -(val['amount'] + vals['amount'])
                        vals['tax_currency_gain'] = 0.0

                        # Check the product are services, which has been using suspend account. This time, it needs to cr: non-suspend acct and dr: suspend acct
                        tax1 = tax_obj.browse(tax['id'])
                        use_suspend_acct = tax1.is_suspend_tax
                        is_wht = tax1.is_wht
                        # -------------------> Adding Tax for Posting
                        if is_wht and not is_taxinv:
                            # Check Threshold first
                            base = company_currency.with_context(ctx).compute((revised_price * line.quantity), invoice.currency_id, round=False)
                            if abs(base) and abs(base) < tax_obj.browse(val['tax_id']).threshold_wht:
                                continue
                            # Case Withholding Tax Dr.
                            if voucher.type in ('receipt', 'payment'):
                                val['base_code_id'] = tax['base_code_id']
                                val['tax_code_id'] = tax['tax_code_id']
                                val['base_amount'] = company_currency.with_context({'date': voucher.date or time.strftime('%Y-%m-%d')}).compute(val['base'] * tax['base_sign'], voucher.currency_id, round=False) * payment_ratio
                                val['tax_amount'] = company_currency.with_context({'date': voucher.date or time.strftime('%Y-%m-%d')}).compute(val['amount'] * tax['tax_sign'], voucher.currency_id, round=False) * payment_ratio
                                val['account_id'] = tax['account_collected_id'] or line.account_id.id
                                val['account_analytic_id'] = tax['account_analytic_collected_id']
                            else:
                                val['base_code_id'] = tax['ref_base_code_id']
                                val['tax_code_id'] = tax['ref_tax_code_id']
                                val['base_amount'] = company_currency.with_context({'date': voucher.date or time.strftime('%Y-%m-%d')}).compute(val['base'] * tax['ref_base_sign'], voucher.currency_id, round=False) * payment_ratio
                                val['tax_amount'] = company_currency.with_context({'date': voucher.date or time.strftime('%Y-%m-%d')}).compute(val['amount'] * tax['ref_tax_sign'], voucher.currency_id, round=False) * payment_ratio
                                val['account_id'] = tax['account_paid_id'] or line.account_id.id
                                val['account_analytic_id'] = tax['account_analytic_paid_id']

                            key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'])
                            if not (key in tax_grouped):
                                tax_grouped[key] = val
                                tax_grouped[key]['amount'] = -tax_grouped[key]['amount']
                                tax_grouped[key]['base'] = -tax_grouped[key]['base']
                                tax_grouped[key]['base_amount'] = -tax_grouped[key]['base_amount']
                                tax_grouped[key]['tax_amount'] = -tax_grouped[key]['tax_amount']
                                tax_grouped[key]['tax_currency_gain'] = 0.0  # No gain loss for WHT
                            else:
                                tax_grouped[key]['amount'] -= val['amount']
                                tax_grouped[key]['base'] -= val['base']
                                tax_grouped[key]['base_amount'] -= val['base_amount']
                                tax_grouped[key]['tax_amount'] -= val['tax_amount']
                                tax_grouped[key]['tax_currency_gain'] -= 0.0  # No gain loss for WHT

                        # -------------------> Adding Tax for Posting 1) Contra-Suspend 2) Non-Suspend
                        elif use_suspend_acct:
                            # First: Do the Cr: with Non-Suspend Account
                            if voucher.type in ('receipt', 'payment'):
                                val['invoice_id'] = invoice.id
                                val['base_code_id'] = tax['base_code_id']
                                val['tax_code_id'] = tax['tax_code_id']
                                val['base_amount'] = cur_obj.compute(voucher.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': voucher.date or time.strftime('%Y-%m-%d')}, round=False) * payment_ratio
                                val['tax_amount'] = cur_obj.compute(voucher.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': voucher.date or time.strftime('%Y-%m-%d')}, round=False) * payment_ratio
                                val['account_id'] = tax['account_collected_id'] or line.account_id.id
                                val['account_analytic_id'] = tax['account_analytic_collected_id']
                            else:
                                val['invoice_id'] = invoice.id
                                val['base_code_id'] = tax['ref_base_code_id']
                                val['tax_code_id'] = tax['ref_tax_code_id']
                                val['base_amount'] = cur_obj.compute(voucher.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': voucher.date or time.strftime('%Y-%m-%d')}, round=False) * payment_ratio
                                val['tax_amount'] = cur_obj.compute(voucher.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': voucher.date or time.strftime('%Y-%m-%d')}, round=False) * payment_ratio
                                val['account_id'] = tax['account_paid_id'] or line.account_id.id
                                val['account_analytic_id'] = tax['account_analytic_paid_id']

#                             if is_taxinv:
#                                 key = (invoice.id)  # Sum all suspended tax for an invoice
#                             else:
#                                 key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'])
                            key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'])

                            if not (key in tax_grouped):
                                tax_grouped[key] = val
                            else:
                                tax_grouped[key]['invoice_id'] = invoice.id  # Speically for taxinv
                                tax_grouped[key]['amount'] += val['amount']
                                tax_grouped[key]['base'] += val['base']
                                tax_grouped[key]['base_amount'] += val['base_amount']
                                tax_grouped[key]['tax_amount'] += val['tax_amount']
                                tax_grouped[key]['tax_currency_gain'] += val['tax_currency_gain']
                            if is_taxinv:
                                continue

                            # Second: Do the Dr: with Suspend Account
                            if voucher.type in ('receipt', 'payment'):
                                vals['base_code_id'] = tax['base_code_id']
                                vals['tax_code_id'] = tax['tax_code_id']
                                vals['base_amount'] = -cur_obj.compute(voucher.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': voucher.date or time.strftime('%Y-%m-%d')}, round=False) * payment_ratio
                                vals['tax_amount'] = -cur_obj.compute(voucher.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': voucher.date or time.strftime('%Y-%m-%d')}, round=False) * payment_ratio
                                # USE SUSPEND ACCOUNT HERE
                                vals['account_id'] = tax['account_suspend_collected_id'] or line.account_id.id
                                vals['account_analytic_id'] = tax['account_analytic_collected_id']
                            else:
                                vals['base_code_id'] = tax['ref_base_code_id']
                                vals['tax_code_id'] = tax['ref_tax_code_id']
                                vals['base_amount'] = -cur_obj.compute(voucher.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': voucher.date or time.strftime('%Y-%m-%d')}, round=False) * payment_ratio
                                vals['tax_amount'] = -cur_obj.compute(voucher.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': voucher.date or time.strftime('%Y-%m-%d')}, round=False) * payment_ratio
                                # USE SUSPEND ACCOUNT HERE
                                vals['account_id'] = tax['account_suspend_paid_id'] or line.account_id.id
                                vals['account_analytic_id'] = tax['account_analytic_paid_id']

                            key = (vals['tax_code_id'], vals['base_code_id'], vals['account_id'], vals['account_analytic_id'])
                            if not (key in tax_grouped):
                                tax_grouped[key] = vals
                            else:
                                tax_grouped[key]['amount'] += vals['amount']
                                tax_grouped[key]['base'] += vals['base']
                                tax_grouped[key]['base_amount'] += vals['base_amount']
                                tax_grouped[key]['tax_amount'] += vals['tax_amount']
                                tax_grouped[key]['tax_currency_gain'] += vals['tax_currency_gain']
                                # --------------------------------------------------------------------------
        # rounding
        for t in tax_grouped.values():
            t['base'] = cur.round(t['base'])
            t['amount'] = cur.round(t['amount'])
            t['base_amount'] = cur.round(t['base_amount'])
            t['tax_amount'] = cur.round(t['tax_amount'])
            t['tax_currency_gain'] = cur.round(t['tax_currency_gain'])
        return tax_grouped
    
    @api.model
    def move_line_get(self, voucher_id):
        res = []
        self._cr.execute('SELECT * FROM account_voucher_tax WHERE voucher_id=%s', (voucher_id,))
        for t in self._cr.dictfetchall():
            if not t['amount'] \
                    and not t['tax_code_id'] \
                    and not t['tax_amount']:
                continue
            res.append({
                'type': 'tax',
                'name': t['name'],
                'price_unit': t['amount'],
                'quantity': 1,
                'price': t['amount'] or 0.0,
                'tax_currency_gain': t['tax_currency_gain'] or 0.0,
                'account_id': t['account_id'],
                'tax_code_id': t['tax_code_id'],
                'tax_amount': t['tax_amount'],
                'account_analytic_id': t['account_analytic_id'],
            })
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
