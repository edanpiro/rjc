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
from openerp.exceptions import except_orm, Warning, RedirectWarning

class hr_expense_expense(models.Model):
    
    @api.one
    @api.depends('expense_vatinfo')
    def _is_vatinfo_tax(self):
            # If any line has vatinfo_tax_amount
        for line in self.expense_vatinfo:
            if line.vatinfo_tax_amount:
                self.is_vatinfo_tax = True
                break

    _inherit = 'hr.expense.expense'
    
    number = fields.Char(string='Expense Number', readonly=True)
    vatinfo_move_id = fields.Many2one('account.move', string='Journal Entry (VAT Info)', readonly=True, select=1, copy=False, ondelete='restrict', help="Link to the automatically generated Journal Items for Vat Info.")
    vatinfo_move_date = fields.Date(related='vatinfo_move_id.date', string="Journal Date (VAT Info)", readonly=True, states={'draft': [('readonly', False)]}, store=True)
    expense_vatinfo = fields.One2many('hr.expense.line', 'expense_id', 'Expense Lines', readonly=False)
    is_vatinfo_tax = fields.Boolean(compute='_is_vatinfo_tax', string='Is VAT Info Tax', store=True, default=False)
    
    @api.model
    def create(self, vals):
        vals['number'] = self.env['ir.sequence'].get('hr.expense.invoice') or '/'
        return super(hr_expense_expense, self).create(vals)
    
    @api.multi
    def expense_confirm(self):
        res = super(hr_expense_expense, self).expense_confirm()
        for expense in self:
            if not expense.number:
                number = self.env['ir.sequence'].get('hr.expense.invoice') or '/'
                self.write({'number': number})
        return res
    
    @api.model
    def line_get_convert(self, x, part, date):
        res = super(hr_expense_expense, self).line_get_convert(x, part, date)
        res.update({'vatinfo_supplier_name': x.get('vatinfo_supplier_name', False)})
        return res
    
    @api.model
    def account_move_get(self, expense_id):
        """
        If journal_id is not forced, use the default as forced journal.
        This is to be used for Post Vat Info action.
        """
        res = super(hr_expense_expense, self).account_move_get(expense_id)
        expense = self.browse(expense_id)
        expense.write({'journal_id': res.get('journal_id', False)})
        return res
    
    @api.multi
    def post_vatinfo(self):
        period_obj = self.env['account.period']
        journal_obj = self.env['account.journal']
        move_obj = self.env['account.move']
        
        for expense in self:
            if not expense.journal_id.sequence_id:
                raise Warning(_('Error!'), _('Please define sequence on the journal related to this expense.'))
            if not expense.line_ids:
                raise Warning(_('No Expense Lines!'), _('Please create some expense lines.'))
            if expense.vatinfo_move_id:
                continue

            ctx = self._context.copy()
            # one move line per expense line
            iml = self.env['hr.expense.line'].with_context(ctx).vatinfo_move_line_get(expense.id)

            date = time.strftime('%Y-%m-%d')
            part = self.env['res.partner']._find_accounting_partner(expense.employee_id.address_home_id)
            line = map(lambda x: (0, 0, self.line_get_convert(x, part, date)), iml)

            journal_id = expense.journal_id.id
            journal = journal_obj.with_context(ctx).browse(journal_id)
            if journal.centralisation:
                raise Warning(_('User Error!'),
                        _('You cannot create an expense on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            line = self.finalize_expense_move_lines(expense, line)

            move = {
                'name': expense.number + '-A',
                'ref': expense.name,
                'line_id': line,
                'journal_id': journal_id,
                'date': date,
                'narration': expense.note,
                'company_id': expense.company_id.id,
            }
            ctx.update(company_id=expense.company_id.id,
                       account_period_prefer_normal=True)
            period_ids = period_obj.with_context(ctx).find(date, context=ctx)
            period_id = period_ids and period_ids[0] or False
            if period_id:
                move['period_id'] = period_id.id
                for i in line:
                    i[2]['period_id'] = period_id.id

            move_id = move_obj.create(move)
            new_move_name = move_id.name
            # make the invoice point to that move
            self.write({'vatinfo_move_id': move_id.id, 'period_id': period_id.id, 'move_name': new_move_name}, context=ctx)
            move_id.with_context(ctx).post()
        return True
    
    @api.model
    def finalize_expense_move_lines(self, expense_browse, move_lines):
        """finalize_expense_move_lines(cr, uid, expense, move_lines) -> move_lines
        Hook method to be overridden in additional modules to verify and possibly alter the
        move lines to be created by an expense, for special cases.
        :param expense_browse: browsable record of the expense that is generating the move lines
        :param move_lines: list of dictionaries with the account.move.lines (as for create())
        :return: the (possibly updated) final move_lines to create for this expense
        """
        return move_lines
    
    @api.multi
    def unpost_vatinfo(self):
        for expense in self:
            expense.vatinfo_move_id.button_cancel()
            self.write({'vatinfo_move_id': False})
            expense.vatinfo_move_id.unlink()
        # self._log_event(cr, uid, ids)
        return True
    
class hr_expense_line(models.Model):
    _inherit = 'hr.expense.line'
    
    vatinfo_date = fields.Date(string='Date', help='This date will be used as Tax Invoice Date in VAT Report')
    vatinfo_number = fields.Char(string='Number', help='Number Tax Invoice')
    vatinfo_supplier_name = fields.Char(string='Supplier', help='Name of Organization to pay Tax')
    vatinfo_tin = fields.Char(string='Tax ID',)
    vatinfo_branch = fields.Char(string='Branch No.')
    vatinfo_base_amount = fields.Float(string='Base', digits_compute=dp.get_precision('Account'))
    vatinfo_tax_id = fields.Many2one('account.tax', string='Tax')
    vatinfo_tax_amount = fields.Float(string='VAT', digits_compute=dp.get_precision('Account'))
    
    @api.onchange('vatinfo_tax_id', 'vatinfo_tax_amount')
    def onchange_vat(self):
        res = {}
        if self.vatinfo_tax_id and self.vatinfo_tax_amount:
            vatinfo_tax = self.vatinfo_tax_id
            tax_percent = vatinfo_tax.amount or 0.0
            if tax_percent > 0.0:
                res['vatinfo_base_amount'] = self.vatinfo_tax_amount / tax_percent
        return {'value': res}
    
    @api.multi
    def action_add_vatinfo(self, data):
        for vatinfo in self:
            if vatinfo.expense_id.vatinfo_move_id:
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
    
    @api.model
    def vatinfo_move_line_get(self, expense_id):
        res = []
        expense = self.env['hr.expense.expense'].browse(expense_id)
        for line in expense.line_ids:
            # No additional vat info, continue
            if not line.vatinfo_tax_amount or line.vatinfo_tax_amount == 0:
                continue
            sign = 1
            account_id = line.vatinfo_tax_id.account_collected_id.id
            # Account Post, deduct from the Expense Line.
            if line.product_id and not line.product_id.property_account_expense:
                raise Warning(_('Error!'), _('Expense Account for this product %s is not defined!') % (line.product_id.name,))
            res.append({
                'type': 'src',
                'name': line.name.split('\n')[0][:64],
                'price_unit':-sign * line.vatinfo_tax_amount,
                'quantity': 1.0,
                'price':-sign * line.vatinfo_tax_amount,
                'account_id': line.product_id and line.product_id.property_account_expense.id or False,
                'product_id': line.product_id and line.product_id.id or False,
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