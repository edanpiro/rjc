# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

import logging
from openerp import models, fields, api, _
_logger = logging.getLogger(__name__)

class account_config_settings(models.TransientModel):
    _inherit = 'account.config.settings'
    
    property_account_add_disc_customer = fields.Many2one('account.account', 'Account Additional Discount Customer')
    property_account_add_disc_supplier =  fields.Many2one('account.account', 'Account Additional Discount Supplier')
    property_account_advance_customer = fields.Many2one('account.account', 'Account Advance Customer')
    property_account_advance_supplier = fields.Many2one('account.account', 'Account Advance Supplier')
    property_account_deposit_customer = fields.Many2one('account.account', 'Account Deposit Customer')
    property_account_deposit_supplier =  fields.Many2one('account.account', 'Account Deposit Supplier')
    property_account_retention_customer = fields.Many2one('account.account', 'Account Retention Customer')
    property_account_retention_supplier = fields.Many2one('account.account', 'Account Retention Supplier')
    
    @api.multi
    def set_default_account_advance(self):
        """ set property advance account for customer and supplier """
        property_obj = self.env['ir.property']
        field_obj = self.env['ir.model.fields']
        todo_list = [
            ('property_account_add_disc_customer', 'res.partner', 'account.account'),
            ('property_account_add_disc_supplier', 'res.partner', 'account.account'),
            ('property_account_advance_customer', 'res.partner', 'account.account'),
            ('property_account_advance_supplier', 'res.partner', 'account.account'),
            ('property_account_deposit_customer', 'res.partner', 'account.account'),
            ('property_account_deposit_supplier', 'res.partner', 'account.account'),
            ('property_account_retention_customer', 'res.partner', 'account.account'),
            ('property_account_retention_supplier', 'res.partner', 'account.account'),
        ]
        for record in todo_list:
            account = getattr(self, record[0])
            value = account and 'account.account,' + str(account.id) or False
            if value:
                field = field_obj.search([('name', '=', record[0]), ('model', '=', record[1]), ('relation', '=', record[2])])
                
                vals = {
                    'name': record[0],
                    'company_id': False,
                    'fields_id': field and field[0].id,
                    'value': value,
                }
                property_ids = property_obj.search([('name', '=', record[0])])
                if property_ids:
                    #the property exist: modify it
                    property_ids.write(vals)
                else:
                    #create the property
                    property_obj.create(vals)
        return True
    
    @api.model
    def get_default_account_advance(self, fields):
        ir_property_obj = self.env['ir.property']
        fiscal_obj = self.env['account.fiscal.position']
        todo_list = [
            ('property_account_add_disc_customer', 'res.partner'),
            ('property_account_add_disc_supplier', 'res.partner'),
            ('property_account_advance_customer', 'res.partner'),
            ('property_account_advance_supplier', 'res.partner'),
            ('property_account_deposit_customer', 'res.partner'),
            ('property_account_deposit_supplier', 'res.partner'),
            ('property_account_retention_customer', 'res.partner'),
            ('property_account_retention_supplier', 'res.partner'),
        ]
        res = {}
        for record in todo_list:
            prop = ir_property_obj.get(record[0], record[1])
            #prop_id = prop and prop.id or False
            account_id = fiscal_obj.map_account(prop)
            res.update({record[0]: account_id.id})
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
