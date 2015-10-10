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
######################################s########################################

from openerp.addons.account.report.account_partner_balance import partner_balance
from openerp.report import report_sxw
from openerp.osv import osv

class partner_balance_ext(partner_balance):

    def set_context(self, objects, data, ids, report_type=None):
        partner_ids = data['form'].get('partner_ids', False)
        if partner_ids:
            res = super(partner_balance_ext, self).set_context(objects, data, partner_ids, report_type)
            self.query += ' AND l.partner_id in (%s) ' % ','.join(str(x) for x in partner_ids)
        else:
            res = super(partner_balance_ext, self).set_context(objects, data, ids, report_type)
        return res

class report_partnerbalance(osv.AbstractModel):
    _name = 'report.account.report_partnerbalance'
    _inherit = 'report.abstract_report'
    _template = 'account.report_partnerbalance'
    _wrapped_report_class = partner_balance_ext

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: