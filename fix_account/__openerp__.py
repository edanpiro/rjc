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
{
    'name' : 'FIX Account',
    'version' : '1.0',
    'author' : 'Ecosoft',
    'category' : 'Accounting & Finance',
    'summary': 'Patch all bugs in account module',
    'description' : """
        1. Fix invoices Analysis,change JOIN condition in sub query of WHERE from alias table cr to cr2
        2. Merge module with fix_account_validate module 
    """,
    'website': 'http://www.ecosoft.co.th',
    'images' : [],
    'depends' : ['account'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
