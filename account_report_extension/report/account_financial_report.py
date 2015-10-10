##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import osv

from openerp.addons.account.report.account_financial_report import report_account_common

class report_account_common_ext(report_account_common):
    _name = "report.account.financial.report_ext"

    def get_lines(self, data):
        lines = super(report_account_common_ext, self).get_lines(data)
        rec_count = len(lines)
        i = 0
        while i < rec_count:
            record = lines[i]
            if data['form'].get('account_type', False):
                if (record['account_type'] != data['form'].get('account_type', False) and record['type'] == 'account'):
                    del lines[i]
                    rec_count = len(lines)
                else:
                    i += 1
            else:
                i += 1
        return lines

class report_financial(osv.AbstractModel):
    _name = 'report.account.report_financial'
    _inherit = 'report.abstract_report'
    _template = 'account.report_financial'
    _wrapped_report_class = report_account_common_ext

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: