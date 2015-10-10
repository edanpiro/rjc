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

import openerp.addons.decimal_precision as dp
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, RedirectWarning, Warning


class invoice_vatinfo(models.TransientModel):

    '''Supplier Invoice VAT Info'''
    
    _name = 'invoice.vatinfo'
    _description = 'Supplier Invoice VAT Info'
    
    @api.model
    def _get_currency_id(self):
        return self.env['account.invoice.line'].browse(self._context['active_id']).invoice_id.currency_id or False
    
    @api.model
    def _get_vatinfo_date(self):
        return self.env['account.invoice.line'].browse(self._context['active_id']).vatinfo_date or False
    
    @api.model
    def _get_vatinfo_number(self):
        return self.env['account.invoice.line'].browse(self._context['active_id']).vatinfo_number or False
    
    @api.model
    def _get_vatinfo_supplier_name(self):
        return self.env['account.invoice.line'].browse(self._context['active_id']).vatinfo_supplier_name or False
    
    @api.model
    def _get_vatinfo_tin(self):
        return self.env['account.invoice.line'].browse(self._context['active_id']).vatinfo_tin or False
    
    @api.model
    def _get_vatinfo_branch(self):
        return self.env['account.invoice.line'].browse(self._context['active_id']).vatinfo_branch or False
    
    @api.model
    def _get_vatinfo_base_amount(self):
        return self.env['account.invoice.line'].browse(self._context['active_id']).vatinfo_base_amount or False
    
    @api.model
    def _get_vatinfo_tax_id(self):
        return self.env['account.invoice.line'].browse(self._context['active_id']).vatinfo_tax_id or False
    
    @api.model
    def _get_vatinfo_tax_amount(self):
        return self.env['account.invoice.line'].browse(self._context['active_id']).vatinfo_tax_amount or False
            
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=_get_currency_id)
    vatinfo_date = fields.Date(string='Date', required=True, help='This date will be used as Tax Invoice Date in VAT Report', default=_get_vatinfo_date)
    vatinfo_number = fields.Char(string='Number', required=True, help='Number Tax Invoice', default=_get_vatinfo_number)
    vatinfo_supplier_name = fields.Char(string='Supplier', required=True, help='Name of Organization to pay Tax', default=_get_vatinfo_supplier_name)
    vatinfo_tin = fields.Char(string='Tax ID', required=True, default=_get_vatinfo_tin)
    vatinfo_branch = fields.Char(string='Branch No.', required=True, default=_get_vatinfo_branch)
    vatinfo_base_amount = fields.Float(string='Base', required=True, digits_compute=dp.get_precision('Account'), default=_get_vatinfo_base_amount)
    vatinfo_tax_id = fields.Many2one('account.tax', string='Tax', domain=[('type_tax_use','=','purchase'), ('is_wht','=',False)], required=True, default=_get_vatinfo_tax_id)
    vatinfo_tax_amount = fields.Float(string='VAT', required=True, digits_compute=dp.get_precision('Account'), default=_get_vatinfo_tax_amount)
    
    @api.one
    def do_add_vatinfo(self):
        invoice_line_obj = self.env['account.invoice.line']
        line_id = self._context['active_id']
        line = invoice_line_obj.browse(line_id)
        line.action_add_vatinfo(self)
        return {'type': 'ir.actions.client', 'tag': 'reload'}   
    
    @api.onchange('vatinfo_base_amount', 'vatinfo_tax_id', 'vatinfo_tax_amount')
    def onchange_vat(self):
        if self.vatinfo_tax_id:
            change_field = self._context.get('change_field', False)
            if self.vatinfo_tax_id and self.vatinfo_tax_id.type == 'percent':
                tax_percent = self.vatinfo_tax_id.amount or 0.0
                if change_field in ['tax_id','base_amt']: 
                    self.vatinfo_tax_amount = round(tax_percent * self.vatinfo_base_amount, 2)
                if change_field == 'tax_amt':
                    self.vatinfo_base_amount = round(self.vatinfo_tax_amount / tax_percent, 2)
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: