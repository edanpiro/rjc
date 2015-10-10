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

from openerp import models, fields, api, _

class account_voucher(models.Model):
    _inherit = 'account.voucher'
    
    reference = fields.Char(string='Ref #', help="Transaction reference number.")
    date_cheque = fields.Date(string='Cheque Date')

class account_voucher_line(models.Model):
    _order = "move_line_id"
    
    @api.multi
    @api.depends('move_line_id')
    def _supplier_invoice_number(self):
        if self.ids:
            self._cr.execute('SELECT vl.id, i.supplier_invoice_number \
                            FROM account_voucher_line vl, account_move_line ml, account_invoice i \
                            WHERE vl.move_line_id = ml.id and ml.move_id = i.move_id \
                            AND vl.id IN %s',
                            (tuple(self.ids),))
            for line_id, supplier_invoice_number in self._cr.fetchall():
                self = self.browse(line_id)
                self.supplier_invoice_number = supplier_invoice_number
    
    _inherit = 'account.voucher.line'
    
    supplier_invoice_number = fields.Char(compute='_supplier_invoice_number', string='Supplier Invoice Number')
#     date_original = fields.Date(related='move_line_id.date', string='Date', store=True, readonly=True) # TODO: No need of this field currently exits in addons


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: