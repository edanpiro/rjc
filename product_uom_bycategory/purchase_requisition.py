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

class purchase_requisition_line(models.Model):
    _inherit = 'purchase.requisition.line'
    
    product_uom_category_id = fields.Integer(string="Product UOM Category ID")
    
    @api.multi
    def onchange_product_id(self, product_id, product_uom_id, parent_analytic_account, analytic_account, parent_date, date):
        res = super(purchase_requisition_line, self).onchange_product_id(product_id, product_uom_id, parent_analytic_account, analytic_account, parent_date, date)
        product = self.env['product.product'].browse(product_id)
        if product.id:
            res['value'].update({'product_uom_category_id': product.uom_id.category_id.id})
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: