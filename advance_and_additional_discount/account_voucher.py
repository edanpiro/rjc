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

class account_voucher_tax(models.Model):
    _inherit = 'account.voucher.tax'
    
    @api.multi
    def compute(self, voucher_id):
        voucher = self.env['account.voucher'].browse(voucher_id)
        
        advance_and_discount = {}
        for voucher_line in voucher.line_ids:
            invoice = voucher_line.move_line_id.invoice
            if invoice:
                adv_disc_param = self.env['account.voucher.line'].get_adv_disc_param(invoice)
                # Add to dict
                advance_and_discount.update({invoice.id: adv_disc_param})
        tax_grouped = super(account_voucher_tax, self).compute_ex(voucher_id, advance_and_discount)
        return tax_grouped

class account_voucher(models.Model):
    _inherit = 'account.voucher'
    
    @api.multi
    def recompute_voucher_lines(self, partner_id, journal_id, price, currency_id, ttype, date):
        # First time, retrieve the voucher lines, this is just to get the invoice ids.
        res = super(account_voucher, self).recompute_voucher_lines(partner_id, journal_id, price, currency_id, ttype, date)
        line_cr_ids = res['value']['line_cr_ids']
        line_dr_ids = res['value']['line_dr_ids']
        move_line_obj = self.env['account.move.line']
        advance_and_discount = {}
        for line in line_cr_ids + line_dr_ids:
	    if not isinstance(line, dict):
                continue
            move_line = move_line_obj.browse(line['move_line_id'])
            invoice = move_line.invoice
            if invoice:
                adv_disc_param = self.env['account.voucher.line'].get_adv_disc_param(invoice)
                # Add to dict
                advance_and_discount.update({invoice.id: adv_disc_param})
        res = self.recompute_voucher_lines_ex(partner_id, journal_id, price, currency_id, ttype, date, advance_and_discount={})
        return res
    
    @api.model
    def _get_amount_wht_ex(self, partner_id, move_line_id, amount_original, original_wht_amt, amount, advance_and_discount={}):
        move_line = self.env['account.move.line'].browse(move_line_id)
        adv_disc_param = {}
        invoice = move_line.invoice
        if invoice:
            adv_disc_param = self.env['account.voucher.line'].get_adv_disc_param(invoice)
            # Add to dict
        amount, amount_wht = super(account_voucher, self)._get_amount_wht_ex(partner_id, move_line_id, amount_original, original_wht_amt, amount, adv_disc_param)
        return float(amount), float(amount_wht)

class account_voucher_line(models.Model):
    _inherit = 'account.voucher.line'
    
    @api.model
    def _get_amount_wht(self, partner_id, move_line_id, amount_original, amount, advance_and_discount={}):
        move_line = self.env['account.move.line'].browse(move_line_id)
        adv_disc_param = {}
        invoice = move_line.invoice
        if invoice:
            adv_disc_param = self.env['account.voucher.line'].get_adv_disc_param(invoice)
        amount, amount_wht = super(account_voucher_line, self)._get_amount_wht(partner_id, move_line_id, amount_original, amount, adv_disc_param)
        return float(amount), float(amount_wht)
    
    @api.model
    def get_adv_disc_param(self, invoice):
        # Percent Additional Discount
        add_disc = invoice.add_disc
        # Percent Advance
        advance_amount = not invoice.is_advance and invoice.amount_advance or 0.0
        advance = invoice.amount_net and advance_amount / (invoice.amount_net) * 100 or 0.0
        # Percent Deposit
        deposit_amount = not invoice.is_deposit and invoice.amount_deposit or 0.0
        deposit = invoice.amount_net and deposit_amount / (invoice.amount_net) * 100 or 0.0
        # Add to dict
        return {'add_disc': add_disc, 'advance': advance, 'deposit': deposit}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
