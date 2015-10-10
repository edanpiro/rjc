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
from openerp.exceptions import except_orm, RedirectWarning, Warning

class account_move(models.Model):
    _inherit = 'account.move'

    # testing: Change power 4 to power 3 when validation. See below.
    # This is the method overwrite of account.validate()
    #
    # Validate a balanced move. If it is a centralised journal, create a move.
    #
    @api.multi
    def validate(self):
        ctx = dict(self._context)
        if ctx and ('__last_update' in ctx):
            del ctx['__last_update']

        valid_moves = []  # Maintains a list of moves which can be responsible to create analytic entries
        obj_move_line = self.env['account.move.line']
        for move in self:
            # Unlink old analytic lines on move_lines
            for obj_line in move.line_id:
                for obj in obj_line.analytic_lines:
                    obj.unlink()

            journal = move.journal_id
            amount = 0
            line_ids = []
            line_draft_ids = []
            company_id = None
            for line in move.line_id:
                amount += line.debit - line.credit
                line_ids.append(line.id)
                if line.state == 'draft':
                    line_draft_ids.append(line.id)

                if not company_id:
                    company_id = line.account_id.company_id.id
                if not company_id == line.account_id.company_id.id:
                    raise Warning(_('Error!'), _("Cannot create moves for different companies."))

                if line.account_id.currency_id and line.currency_id:
                    if line.account_id.currency_id.id != line.currency_id.id and (line.account_id.currency_id.id != line.account_id.company_id.currency_id.id):
                        raise Warning(_('Error!'), _("""Cannot create move with currency different from ..""") % (line.account_id.code, line.account_id.name))
            
            # testing
            if abs(amount) < 10 ** -1:
            # -- testing
                # If the move is balanced
                # Add to the list of valid moves
                # (analytic lines will be created later for valid moves)
                valid_moves.append(move)

                # Check whether the move lines are confirmed

                if not line_draft_ids:
                    continue
                # Update the move lines (set them as valid)
                
                move_line = obj_move_line.browse(line_draft_ids) 
                
                move_line.with_context(ctx).write({
                    'state': 'valid'
                }, check=False)

                account = {}
                account2 = {}

                if journal.type in ('purchase', 'sale'):
                    for line in move.line_id:
                        code = amount = 0
                        key = (line.account_id.id, line.tax_code_id.id)
                        if key in account2:
                            code = account2[key][0]
                            amount = account2[key][1] * (line.debit + line.credit)
                        elif line.account_id.id in account:
                            code = account[line.account_id.id][0]
                            amount = account[line.account_id.id][1] * (line.debit + line.credit)
                        if (code or amount) and not (line.tax_code_id or line.tax_amount):
                            line.with_context(ctx).write({
                                'tax_code_id': code,
                                'tax_amount': amount
                            }, check=False)
            elif journal.centralisation:
                # If the move is not balanced, it must be centralised...

                # Add to the list of valid moves
                # (analytic lines will be created later for valid moves)
                valid_moves.append(move)

                #
                # Update the move lines (set them as valid)
                #
                self._centralise(move, 'debit')
                self._centralise(move, 'credit')
                move_line.write({
                    'state': 'valid'
                }, check=False)
            else:
                # We can't validate it (it's unbalanced)
                # Setting the lines as draft
                lines = obj_move_line.browse(line_ids) 
                lines.with_context(ctx).write({
                    'state': 'draft'
                }, check=False)
        # Create analytic lines for the valid moves
        for record in valid_moves:
            record.line_id.create_analytic_lines()

        valid_moves = [move.id for move in valid_moves]
        return len(valid_moves) > 0 and valid_moves or False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: