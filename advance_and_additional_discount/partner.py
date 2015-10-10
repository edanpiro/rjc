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

from openerp import api, fields, models, _

class res_partner(models.Model):
    _inherit = 'res.partner'

    property_account_add_disc_customer = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Account Additional Discount Customer",
        domain="[('type', '=', 'payable')]",
        help="This account will be used instead of the default one as the additional discount account for the current partner",
        required=True,
        readonly=True)
    property_account_add_disc_supplier = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Account Additional Discount Supplier",
        domain="[('type', '=', 'receivable')]",
        help="This account will be used instead of the default one as the additional discount account for the current partner",
        required=True,
        readonly=True)
    property_account_advance_customer = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Account Advance Customer",
        domain="[('type', '=', 'payable')]",
        help="This account will be used instead of the default one as the advance account for the current partner",
        required=True,
        readonly=True)
    property_account_advance_supplier = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Account Advance Supplier",
        domain="[('type', '=', 'receivable')]",
        help="This account will be used instead of the default one as the advance account for the current partner",
        required=True,
        readonly=True)
    property_account_deposit_customer = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Account Deposit Customer",
        domain="[('type', '=', 'payable')]",
        help="This account will be used instead of the default one as the deposit account for the current partner",
        required=True,
        readonly=True)
    property_account_deposit_supplier = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Account Deposit Supplier",
        domain="[('type', '=', 'receivable')]",
        help="This account will be used instead of the default one as the deposit account for the current partner",
        required=True,
        readonly=True)
    property_account_retention_customer = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Account Retention Customer",
        domain="[('type', '=', 'payable')]",
        help="This account will be used instead of the default one as the retention account for the current partner",
        required=True,
        readonly=True)
    property_account_retention_supplier = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Account Retention Supplier",
        domain="[('type', '=', 'receivable')]",
        help="This account will be used instead of the default one as the retention account for the current partner",
        required=True,
        readonly=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: