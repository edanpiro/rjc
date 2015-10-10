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

class hr_expense_expense(models.Model):
    _inherit = 'hr.expense.expense'
    
    @api.one
    @api.depends('account_move_id', 'account_move_id.line_id')
    def _compute_lines(self):
        lines = []
        src = []
        for expense in self:
            if expense.account_move_id:
                for m in expense.account_move_id.line_id:
                    temp_lines = []
                    if m.reconcile_id:
                        temp_lines = map(lambda x: x.id, m.reconcile_id.line_id)
                    elif m.reconcile_partial_id:
                        temp_lines = map(lambda x: x.id, m.reconcile_partial_id.line_partial_ids)
                    lines += [x for x in temp_lines if x not in lines]
                    src.append(m.id)
 
            lines = filter(lambda x: x not in src, lines)
        self.payment_ids = lines
    
    payment_ids = fields.Many2many('account.move.line', string='Payments', compute='_compute_lines')
    
    @api.multi
    def expense_canceled(self):     
        expenses = self.read(['account_move_id', 'payment_ids'])
        move_ids = []  # ones that we will need to remove
        for expense in expenses:
            if expense['account_move_id']:
                move_ids.append(expense['account_move_id'][0])
            if expense['payment_ids']:
                account_move_line_obj = self.env['account.move.line']
                pay_ids = account_move_line_obj.browse(expense['payment_ids'])
                for move_line in pay_ids:
                    if move_line.reconcile_partial_id and move_line.reconcile_partial_id.line_partial_ids:
                        raise Warning(_('Error!'), _('You cannot cancel an expense which is partially paid. You need to unreconcile related payment entries first.'))

        # First, detach the move ids
        self.write({'move_id':False})
        if move_ids:
            # second, invalidate the move(s)
            moves = self.env['account.move'].browse(move_ids)
            moves.button_cancel()
            # delete the move this invoice was pointing to
            # Note that the corresponding move_lines and move_reconciles
            # will be automatically deleted too
            moves.unlink()

        # Call super method.
        res = super(hr_expense_expense, self).expense_canceled()
        return res
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: