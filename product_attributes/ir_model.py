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

from openerp import fields, models

class ir_model_fields(models.Model):
    _inherit = 'ir.model.fields'
        # Change size to 256 to support this module.
    selection = fields.Char(string='Selection Options', help="List of options for a selection field, "
        "specified as a Python expression defining a list of (key, label) pairs. "
        "For example: [('blue','Blue'),('yellow','Yellow')]")
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: