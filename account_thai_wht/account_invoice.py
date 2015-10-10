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
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools import float_compare

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    # Overwrite
    @api.one
    @api.depends('invoice_line', 'invoice_line.price_subtotal')
    def _amount_all(self):
        for line in self.invoice_line:
            self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
        for line in self.tax_line:  # Exclude WHT
            if not line.is_wht:
                self.amount_tax += line.amount
        self.amount_total = self.amount_tax + self.amount_untaxed

    # Overwrite
    amount_untaxed = fields.Float(compute='_amount_all', digits_compute=dp.get_precision('Account'), string='Subtotal', track_visibility='always', store=True, multi='all')
    amount_tax = fields.Float(compute='_amount_all', digits_compute=dp.get_precision('Account'), string='Tax', store=True, multi='all')
    amount_total = fields.Float(compute='_amount_all', digits_compute=dp.get_precision('Account'), string='Total', store=True, multi='all') 
    
    @api.multi
    def check_tax_lines(self, compute_taxes):
        account_invoice_tax = self.env['account.invoice.tax']
        company_currency = self.company_id.currency_id
        if not self.tax_line:
            for tax in compute_taxes.values():
                account_invoice_tax.create(tax)
        else:
            tax_key = []
            precision = self.env['decimal.precision'].precision_get('Account')
            for tax in self.tax_line:
                if tax.manual:
                    continue
                key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id, tax.account_analytic_id.id)
                tax_key.append(key)
                if key not in compute_taxes:
                    raise except_orm(_('Warning!'), _('Global taxes defined, but they are not in invoice lines !'))
                base = compute_taxes[key]['base']
                if float_compare(abs(base - tax.base), company_currency.rounding, precision_digits=precision) == 1:
                    raise except_orm(_('Warning!'), _('Tax base different!\nClick on compute to update the tax base.'))
            for key in compute_taxes:
                if key not in tax_key:
                    raise except_orm(_('Warning!'), _('Taxes are missing!\nClick on compute button.'))               

class account_invoice_tax(models.Model):
    _inherit = 'account.invoice.tax'
    
    is_wht = fields.Boolean(string='Withholding Tax', readonly=True, help='Tax will be withhold and will be used in Payment')
    
    @api.multi
    def compute(self, invoice_id):
        tax_grouped = self.compute_ex(invoice_id, add_disc=0.0, advance=0.0, deposit=0.0)
        return tax_grouped

    # Enhanced from compute() method, to detail with Additional Discount / Advance / Deposit
    @api.multi
    def compute_ex(self, inv, add_disc=0.0, advance=0.0, deposit=0.0):
        tax_grouped = {}
        tax_obj = self.env['account.tax']
        cur = inv.currency_id
        company_currency = inv.company_id.currency_id

        for line in inv.invoice_line:
            revised_price = (line.price_unit * (1 - (line.discount or 0.0) / 100.0) * (1 - (add_disc or 0.0) / 100.0) * (1 - (advance or 0.0) / 100.0) * (1 - (deposit or 0.0) / 100.0))
            for tax in line.invoice_line_tax_id.compute_all(revised_price, line.quantity, line.product_id, inv.partner_id)['taxes']:
                val = {}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = cur.round(tax['price_unit'] * line['quantity'])
                val['is_wht'] = tax_obj.browse(tax['id']).is_wht
                
                ctx = dict(self._context or {})
                ctx.update({'date': inv.date_invoice or time.strftime('%Y-%m-%d')})
                if val['is_wht']:
                    # Check Threshold first (with document's currency
                    base = company_currency.with_context(ctx).compute((revised_price * line.quantity), inv.currency_id, round=False)
                    if abs(base) and abs(base) < tax_obj.browse(tax['id']).threshold_wht:
                        continue

                use_suspend_acct = tax_obj.browse(tax['id']).is_suspend_tax

                if inv.type in ('out_invoice', 'in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = company_currency.with_context(ctx).compute(val['base'] * tax['base_sign'], inv.currency_id, round=False)
                    val['tax_amount'] = company_currency.with_context(ctx).compute(val['amount'] * tax['tax_sign'], inv.currency_id, round=False)

                    # start testing for Thai Accounting
                    # val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_id'] = use_suspend_acct and tax['account_suspend_collected_id'] or tax['account_collected_id'] or line.account_id.id
                    # end testing
                    
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = company_currency.with_context({'date': inv.date_invoice or time.strftime('%Y-%m-%d')}).compute(val['base'] * tax['ref_base_sign'], inv.currency_id, round=False)
                    val['tax_amount'] = company_currency.with_context({'date': inv.date_invoice or time.strftime('%Y-%m-%d')}).compute(val['amount'] * tax['ref_tax_sign'], inv.currency_id, round=False)
                    # start testing
                    # val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_id'] = use_suspend_acct and tax['account_suspend_paid_id'] or tax['account_collected_id'] or line.account_id.id
                    # end testing                    
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']
                    tax_grouped[key]['is_wht'] = val['is_wht']

        for t in tax_grouped.values():
            t['base'] = cur.round(t['base'])
            t['amount'] = cur.round(t['amount'])
            t['base_amount'] = cur.round(t['base_amount'])
            t['tax_amount'] = cur.round(t['tax_amount'])
        return tax_grouped
    
    @api.model
    def move_line_get(self, invoice_id):
        res = []
        self._cr.execute('SELECT * FROM account_invoice_tax WHERE is_wht=False and invoice_id=%s', (invoice_id,))
        for t in self._cr.dictfetchall():
            if not t['amount'] \
                    and not t['tax_code_id'] \
                    and not t['tax_amount']:
                continue
            res.append({
                'type':'tax',
                'name':t['name'],
                'price_unit': t['amount'],
                'quantity': 1,
                'price': t['amount'] or 0.0,
                'account_id': t['account_id'],
                'tax_code_id': t['tax_code_id'],
                'tax_amount': t['tax_amount'],
                'account_analytic_id': t['account_analytic_id'],
            })
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: