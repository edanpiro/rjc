# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 CamptoCamp
# Copyright (c) 2006-2010 OpenERP S.A
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################

from openerp.addons.account.report.account_general_ledger import general_ledger
from openerp.report import report_sxw
from openerp.osv import osv

# class general_ledger_ext(general_ledger):
# 
#     def set_context(self, objects, data, ids, report_type=None):
#         account_ids = data['form'].get('account_ids', False)
#         if account_ids:
#             res = super(general_ledger_ext, self).set_context(objects, data, account_ids, report_type)
#             #self.query+=" AND l.account_id = (select id from account_account a  where a.id = l.account_id and  type1 not in ('view') )"
#             self.query += ' AND l.account_id in (%s) ' % ','.join(str(x) for x in account_ids)
#             self.init_query += ' AND l.account_id in (%s) ' % ','.join(str(x) for x in account_ids)
#         else:
#             res = super(general_ledger_ext, self).set_context(objects, data, ids, report_type)
#         return res
# 
# class report_generalledger(osv.AbstractModel):
#     _name = 'report.account.report_generalledger'
#     _inherit = 'report.abstract_report'
#     _template = 'account.report_generalledger'
#     _wrapped_report_class = general_ledger_ext

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: