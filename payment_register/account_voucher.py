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
# TODO
# - Only create Payment Register, if Type = Receipt

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_voucher(models.Model):
    
    @api.one
    @api.depends('payment_details')
    def _amount_all(self):
        val = 0.0
        for line in self.payment_details:
            val += line.amount
        self.amount_total = val
    
    @api.model
    def _get_journal(self):
        # Ignore the more complex account_voucher._get_journal() and simply return Bank in tansit journal.
        type = self._context.get('type', False)
        if type and type == 'receipt':
            res = self.env.ref('payment_register.bank_intransit_journal', False)
            return res or False
        else:
            res = self._make_journal_search('bank')
            return res and res[0] or False
        return False

    _inherit = 'account.voucher'
    #_rec_name = 'number'
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, default=_get_journal)
    payment_details = fields.One2many('account.voucher.pay.detail', 'voucher_id', string='Payment Details')
    amount_total = fields.Float(compute='_amount_all', digits_compute=dp.get_precision('Account'), string='Total',
                                store=True, multi='sums', help="The total amount.")
    is_paydetail_created = fields.Boolean(string='Payment Details Created', readonly=True)

    @api.multi
    def name_get(self):
        return [(r['id'], r['number'] or '') for r in self.read(['number'], load='_classic_write')]
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        recs = self.browse()
        if name:
            recs = self.search([('number', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    @api.multi
    def create_payment_register(self):
        # Validate Payment and Payment Detail Amount
        if self.type == 'receipt':
            if (self.amount_total or 0.0) != (self.amount or 0.0):
                raise Warning(_('Unable to save!'), _('Total Amount in Payment Details must equal to Paid Amount'))
        payment_register_pool = self.env['payment.register']
        for voucher in self:
            if voucher.type != 'receipt':  # Only on receipt case.
                continue
            # For each of the Payment Detail, create a new payment detail.
            period_pool = self.env['account.period']
            ctx = dict(self._context)
            ctx.update({'company_id': voucher.company_id.id})
            for payment_detail in voucher.payment_details:
                pids = period_pool.with_context(ctx).find(payment_detail.date_due)
                res = {
                    'voucher_id': voucher.id,
                    'pay_detail_id': payment_detail.id,
                    'name': payment_detail.name,
                    'type': payment_detail.type,
                    'check_no': payment_detail.check_no,
                    'date_due': payment_detail.date_due,
                    'original_pay_currency_id': voucher.currency_id and voucher.currency_id.id or voucher.company_id.currency_id.id,
                    'original_pay_amount': payment_detail.amount,
                    'amount': payment_detail.amount,
                    'date': payment_detail.date_due,
                    'period_id': pids and pids[0].id or False,
                }
                payment_register_pool.create(res)
            voucher.write({'is_paydetail_created': True})
        return True
    
    @api.multi
    def cancel_voucher(self):
        # If this voucher has related payment register, make sure all of them are cancelled first.
        payment_register_pool = self.env['payment.register']
        for voucher in self:
            register_ids = payment_register_pool.search([('voucher_id', '=', voucher.id), ('state', '<>', 'cancel')], limit=1)
            if register_ids:  # if at least 1 record not cancelled, raise error
                raise Warning(_('Error!'), _('You can not cancel this Payment.\nYou need to cancel all Payment Details associate with this payment first.'))
            register_ids = payment_register_pool.search([('voucher_id', '=', voucher.id)])
            if register_ids == []:  # All register has been deleted.
                voucher.write({'is_paydetail_created': False})
        # Normal call
        res = super(account_voucher, self).cancel_voucher()
        return res
    
    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default.update(is_paydetail_created=False)
        return super(account_voucher, self).copy(default)

class account_voucher_pay_detail(models.Model):
    _name = 'account.voucher.pay.detail'
    _description = 'Payment Details'

    name = fields.Char(string='Bank/Branch')
    voucher_id = fields.Many2one('account.voucher', string='Voucher Reference', ondelete='cascade', select=True)
    type = fields.Selection(selection=[
            ('check', 'Check'),
            ('cash', 'Cash'),
            ('transfer', 'Transfer')
            ], string='Type', required=True, select=True, change_default=True)
    check_no = fields.Char(string='Check No.')
    date_due = fields.Date(string='Check Date')
    amount = fields.Float(string='Amount', digits_compute=dp.get_precision('Account'))
    #'date_payin': fields.date('Pay-in Date'),

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
