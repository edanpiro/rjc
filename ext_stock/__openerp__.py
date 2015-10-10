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
    'name' : 'Stock Extension for RJC',
    'version' : '1.0',
    'author' : 'Kitti U.',
    'summary': 'Miscellenous Extension to Stock Module for RJC',
    'description': """

This module includes:

* Adding Group By Partner in Deliver Product's Search
* Adding Group By Partner in Deliver Order's Search
* Adding field "Description" in Delivery Order Lines
* Only show buttons in "Stock Move Detail" in case of Internal Move. Hiding buttons when Incoming Shipment / Delivery Orders
* In deliver wizard form, remove "Add items" link.
* Deliver Order search, including Customer name.
* Adding a new field in Delivery Order, "Printed?". This field will be marked when Delivery Slip (RJC) is printed.
* Do not allow delivery quantity > initial quantity in the DO.
* Adding "Date of Reception" on Receive Dialog (wizard). Use this date to update "Date of Reception" in "Incoming Shipment"

    """,
    'category': 'Warehouse Management',
    'sequence': 4,
    'website' : 'http://www.ecosoft.co.th',
    'images' : [],
    'depends' : ['stock', 'rml_reports'],
    'demo' : [],
    'data' : [
        'stock_view.xml',
#         'wizard/stock_partial_picking_view.xml'
    ],
    'test' : [
    ],
    'auto_install': False,
    'application': True,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
