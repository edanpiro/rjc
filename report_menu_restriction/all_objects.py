# -*- coding: utf-8 -*-
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

from openerp import api, fields, models, _

# Remove report from the list, if the view security is assigned.
def check_print_list(result):
    view_id = result.get('view_id', False)
    if result.get('toolbar', False):
        reports = result['toolbar']['print'][:]  # Pass by value
        i = 0
        for report in reports:
            if report['views_id']:
                if view_id not in report['views_id']:
                    result['toolbar']['print'].pop(i)
                    i = i - 1
            i = i + 1
    return result

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(account_invoice, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        result = check_print_list(result)
        return result
    
class account_voucher(models.Model):
    _inherit = 'account.voucher'
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(account_voucher, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        result = check_print_list(result)
        return result
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
