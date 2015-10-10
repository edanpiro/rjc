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
#    MERCHANTABILITY or FITNESS FOR A P fields,ARTICULAR PURPOSE.  See the
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

class account_billing(models.Model):
    
    @api.model
    def _get_journal(self):
        # Ignore the more complex account_voucher._get_journal() and simply return Bank in tansit journal.
        res = self.env.ref('payment_register.bank_intransit_journal', False)
        return res and res.id or False
    
    _inherit = 'account.billing'
    
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True, default=_get_journal)                
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: