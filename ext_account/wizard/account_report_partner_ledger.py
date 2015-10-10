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

from openerp import models, api, fields, _

class account_partner_ledger(models.TransientModel):
    _inherit = 'account.partner.ledger'

    filter = fields.Selection(selection=[
                ('filter_no', 'No Filters'),
                ('filter_partner', 'Partner'),
                ('filter_date', 'Date'),
                ('filter_period', 'Periods'),
                ('unreconciled', 'Unreconciled Entries')], string="Filter by", required=True),
    partner_id = fields.Many2one('res.partner', string='Partner')

    @api.multi    
    def onchange_filter(self, filter='filter_no', fiscalyear_id=False):
        res = super(account_partner_ledger, self).onchange_filter(filter=filter, fiscalyear_id=fiscalyear_id)
        if filter == 'filter_partner':
            res['value'].update({'initial_balance': False, 'period_from': False, 'period_to': False, 'date_from': False , 'date_to': False})
        return res
    
    @api.multi
    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'filter', 'page_split', 'amount_currency'])[0])
        if data['form'].get('page_split') is True: 
            return self.pool['report'].get_action('account.report_partnerledgerother', data=data)
        return self.pool['report'].get_action('account.report_partnerledger', data=data)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: