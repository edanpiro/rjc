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
    'name' : 'Sale Extension for RJC',
    'version' : '1.0',
    'author' : 'Kitti U.',
    'summary': 'Miscellenous Extension to Sale Module for RJC',
    'description': """

This module includes:

* New field "Special Instruction" in Sales Order Line. Also passing this bit of information to DO and INV
* Invoice Line -- Adding new "Serial Number" field. If DO has this value, when Invoice is created, the value will be coped over here.
* in SO window, filter Invoice Address and Delivery Address based on Customer.
    """,
    'category': 'Sales Management',
    'sequence': 6,
    'website' : 'http://www.ecosoft.co.th',
    'images' : [],
    'depends' : ['sale', 'stock', 'sale_stock', 'account', 'account_invoice_merge'],
    'demo' : [],
    'data' : [
        'sale_view.xml',
        'stock_view.xml',
        'account_invoice_view.xml'
    ],
    'test' : [],
    'auto_install': False,
    'application': True,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: