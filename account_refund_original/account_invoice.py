# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2011
#        Pexego Sistemas Informáticos. (http://pexego.es) All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

__author__ = "Luis Manuel Angueira Blanco (Pexego)"

"""
Inheritance of account invoce to add some fields.
"""

from openerp import api, fields, models, _

class account_invoice(models.Model):
    """
    Inheritance of account invoce to add some fields
    """
    _inherit = 'account.invoice'

    refund_invoices_description = fields.Text(string='Refund invoices description')
    origin_invoices_ids = fields.Many2many('account.invoice', 'account_invoice_refunds_rel', 'refund_invoice_id', 'original_invoice_id', string='Refund invoice',
                                            help='Links to original invoice which is referred by current refund invoice')
    

