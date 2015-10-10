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
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_invoice(models.Model):
    
    @api.one
    @api.depends('invoice_vatinfo', 'invoice_vatinfo.vatinfo_tax_amount')
    def _is_vatinfo_tax(self):
        # If any line has vatinfo_tax_amount
        for line in self.invoice_vatinfo:
            if line.vatinfo_tax_amount:
                self.is_vatinfo_tax = True
                break
            
    _inherit = 'account.invoice'

    vatinfo_move_id = fields.Many2one('account.move', string='Journal Entry (VAT Info)', readonly=True, copy=False, select=1, ondelete='restrict', help="Link to the automatically generated Journal Items for Vat Info.")
    vatinfo_move_date = fields.Date(related='vatinfo_move_id.date', string="Journal Date (VAT Info)", readonly=True)
    invoice_vatinfo = fields.One2many('account.invoice.line', 'invoice_id', string='Invoice Lines', readonly=True, states={'draft': [('readonly', False)]})
    is_vatinfo_tax = fields.Boolean(compute='_is_vatinfo_tax', string='Is VAT Info Tax', store=True)
    
    @api.model
    def line_get_convert(self, x, part, date):
        res = super(account_invoice, self).line_get_convert(x, part, date)
        res.update({'vatinfo_supplier_name': x.get('vatinfo_supplier_name', False)})
        return res
    
    @api.multi
    def post_vatinfo(self):
        period_obj = self.env['account.period']
        move_obj = self.env['account.move']
        for inv in self:
            if not inv.journal_id.sequence_id:
                raise Warning(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise Warning(_('No Invoice Lines!'), _('Please create some invoice lines.'))
            if inv.vatinfo_move_id:
                continue

            ctx = dict(self._context)
            ctx.update({'lang': inv.partner_id.lang})
            # one move line per invoice line
            iml = self.env['account.invoice.line'].with_context(ctx).vatinfo_move_line_get(inv)

            date = time.strftime('%Y-%m-%d')
            part = inv.partner_id._find_accounting_partner()
            line = map(lambda x: (0, 0, self.with_context(ctx).line_get_convert(x, part.id, date)), iml)
            line = inv.group_lines(iml, line)

            if inv.journal_id.centralisation:
                raise Warning(_('User Error!'),
                        _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            line = inv.finalize_invoice_move_lines(line)

            move = {
                'name': inv.number + '-VAT',
                'ref': inv.name,
                'line_id': line,
                'journal_id': inv.journal_id.id,
                'date': date,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
            }
            ctx.update(company_id=inv.company_id.id, account_period_prefer_normal=True)
            period_ids = period_obj.with_context(ctx).find(date)
            period_id = period_ids and period_ids[0] or False
            if period_id:
                move['period_id'] = period_id.id
                for i in line:
                    i[2]['period_id'] = period_id.id

            ctx.update(invoice=inv)
            move_id = move_obj.with_context(ctx).create(move)
            new_move_name = move_id.name
            # make the invoice point to that move
            self.with_context(ctx).write({'vatinfo_move_id': move_id.id, 'period_id': period_id.id, 'move_name': new_move_name})
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move_id.with_context(ctx).post()
        self._log_event()
        return True
    
    @api.multi
    def unpost_vatinfo(self):
        for inv in self:
            move_id = inv.vatinfo_move_id
            move_id.button_cancel()
            inv.write({'vatinfo_move_id': False})
            move_id.unlink()
        self._log_event()
        return True

class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'
    
    vatinfo_date = fields.Date(string='Date', help='This date will be used as Tax Invoice Date in VAT Report')
    vatinfo_number = fields.Char(string='Number', help='Number Tax Invoice')
    vatinfo_supplier_name = fields.Char(string='Supplier', help='Name of Organization to pay Tax')
    vatinfo_tin = fields.Char(string='Tax ID')
    vatinfo_branch = fields.Char(string='Branch No.')
    vatinfo_base_amount = fields.Float(string='Base', digits_compute=dp.get_precision('Account'))
    vatinfo_tax_id = fields.Many2one('account.tax', string='Tax')
    vatinfo_tax_amount = fields.Float(string='VAT', digits_compute=dp.get_precision('Account'))
    
    @api.onchange('vatinfo_tax_id')
    def onchange_vat(self):
        if self.vatinfo_tax_id and self.vatinfo_tax_amount:
            tax_percent = self.vatinfo_tax_id.amount or 0.0
            if tax_percent > 0.0:
                self.vatinfo_base_amount = self.vatinfo_tax_amount / tax_percent

    @api.one
    def action_add_vatinfo(self, data):
        for vatinfo in self:
            if vatinfo.invoice_id.vatinfo_move_id:
                raise Warning(_('Error!'),
                    _('VAT Info can be changed only when it is not posted. \n' + 
                      'To change, Unpost VAT Info first.'))

            vatinfo.write({
                'vatinfo_date': data.vatinfo_date,
                'vatinfo_number': data.vatinfo_number,
                'vatinfo_supplier_name': data.vatinfo_supplier_name,
                'vatinfo_tin': data.vatinfo_tin,
                'vatinfo_branch': data.vatinfo_branch,
                'vatinfo_base_amount': data.vatinfo_base_amount,
                'vatinfo_tax_id': data.vatinfo_tax_id.id,
                'vatinfo_tax_amount': data.vatinfo_tax_amount
            })
        return True
    
    @api.multi
    def vatinfo_move_line_get(self, inv):
        res = []
        for line in inv.invoice_line:
            # No additional vat info, continue
            if not line.vatinfo_tax_amount or line.vatinfo_tax_amount == 0:
                continue

            sign = 1
            account_id = 0
            if inv.type in ('out_invoice', 'in_invoice'):
                sign = 1
                account_id = line.vatinfo_tax_id.account_collected_id.id
            else:
                sign = -1
                account_id = line.vatinfo_tax_id.account_paid_id.id

            # Account Post, deduct from the Invoice Line.
            res.append({
                'type': 'src',
                'name': line.name.split('\n')[0][:64],
                'price_unit':-sign * line.vatinfo_tax_amount,
                'quantity': 1.0,
                'price':-sign * line.vatinfo_tax_amount,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'uos_id': False,
                'account_analytic_id': False,
                'taxes': False,
            })

            # Account Post, Tax
            res.append({
                'type': 'tax',
                'name': line.vatinfo_tax_id.name,
                'price_unit': sign * line.vatinfo_tax_amount,
                'quantity': 1,
                'price': sign * line.vatinfo_tax_amount,
                'account_id': account_id,
                'product_id': False,
                'uos_id': False,
                'account_analytic_id': False,
                'taxes': False,
                'vatinfo_supplier_name': line.vatinfo_supplier_name,
            })

        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: