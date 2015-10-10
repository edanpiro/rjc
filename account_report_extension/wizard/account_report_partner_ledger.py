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

from openerp import models, api


class account_partner_ledger(models.TransientModel):
    """
    This wizard will provide the partner Ledger report by periods, between any two dates.
    """
    _name = 'account.partner.ledger'
    _inherit = ['account.partner.ledger', 'account.common.partner.report']
    _description = 'Account Partner Ledger'

    @api.v7        
    def _print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        data['form'].update(self.read(cr, uid, ids, ['initial_balance', 'filter', 'page_split', 'amount_currency', 'partner_ids'])[0])
        if data['form'].get('page_split') is True: 
            return self.pool['report'].get_action(cr, uid, [], 'account.report_partnerledgerother', data=data, context=context)
        return self.pool['report'].get_action(cr, uid, [], 'account.report_partnerledger', data=data, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: