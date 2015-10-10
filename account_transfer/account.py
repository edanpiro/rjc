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

class account_journal(models.Model):
    have_partner = fields.Boolean(string='Require Partner')
    account_transit = fields.Many2one('account.account', string='Account Transit', help="Account used to make money transfers between bank and cash journals")

    _name = 'account.journal'
    _inherit = 'account.journal'

class account_voucher(models.Model):
    transfer_id = fields.Many2one('account.transfer', string='Money Transfer', readonly=True, states={'draft':[('readonly', False)]})
    type = fields.Selection(selection=[
                         ('sale', 'Sale'),
                         ('purchase', 'Purchase'),
                         ('payment', 'Payment'),
                         ('receipt', 'Receipt'),
                         ('transfer', 'Transfer'),
                         ], string='Default Type', readonly=True, states={'draft':[('readonly', False)]})
    _name = 'account.voucher'
    _inherit = 'account.voucher'

    _document_type = {
        'sale': 'Sales Receipt',
        'purchase': 'Purchase Receipt',
        'payment': 'Supplier Payment',
        'receipt': 'Customer Payment',
        'transfer': 'Money Transfer',
        False: 'Payment',
    }
    
    @api.model
    def first_move_line_get(self, voucher_id, move_id, company_currency, current_currency):
        res = super(account_voucher,self).first_move_line_get(voucher_id, move_id, company_currency, current_currency)
        voucher = self.env['account.voucher'].browse(voucher_id)
        if voucher.type == 'transfer':
            #import pdb; pdb.set_trace()
            if voucher.transfer_id.src_journal_id.id == voucher.journal_id.id:
                res['credit'] = voucher.paid_amount_in_company_currency
            else:
                res['debit'] = voucher.paid_amount_in_company_currency
            if res['debit'] < 0: res['credit'] = -res['debit']; res['debit'] = 0.0
            if res['credit'] < 0: res['debit'] = -res['credit']; res['credit'] = 0.0
            sign = res['debit'] - res['credit'] < 0 and -1 or 1
            res['currency_id'] = company_currency <> current_currency and current_currency or False
            res['amount_currency'] = company_currency <> current_currency and sign * voucher.amount or 0.0
        return res
