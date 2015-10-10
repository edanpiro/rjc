# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#        Zikzakmedia S.L. (http://zikzakmedia.com) All Rights Reserved.
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

__author__ = "Jordi Esteve <jesteve@zikzakmedia.com> (Zikzakmedia)"


from openerp import api, models, _

class account_invoice_refund(models.TransientModel):
    '''Refunds invoice'''

    _inherit = 'account.invoice.refund'
    
    @api.multi
    def compute_refund(self, mode='refund'):
        '''
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: the account invoice refund’s ID or list of IDs

        '''
        inv_obj = self.env['account.invoice']
        result = super(account_invoice_refund, self).compute_refund(mode)
        # An example of result['domain'] computed by the parent wizard is:
        # [('type', '=', 'out_refund'), ('id', 'in', [43L, 44L])]
        # The created refund invoice is the first invoice in the ('id', 'in', ...) tupla
        created_inv = [x[2] for x in result['domain'] if x[0] == 'id' and x[1] == 'in']
        if self._context.get('active_ids') and created_inv and created_inv[0]:
            for form in self:
                refund_inv_id = created_inv[0][0]
                refund_inv = inv_obj.browse(refund_inv_id)
                refund_inv.write({
                    'origin_invoices_ids': [(6, 0, self._context.get('active_ids'))],
                    'refund_invoices_description': form.description or ''
                })
        return result
