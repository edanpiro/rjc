# -*- encoding: utf-8 -*-
############################################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2010 Zikzakmedia S.L. (<http://www.zikzakmedia.com>). All Rights Reserved
#    $Id$
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
############################################################################################

from openerp import api, fields, models, _
from openerp.exceptions import Warning

FIELD_FILTER = ['property']

class product_attributes_wizard(models.TransientModel):
    _name = 'product.attributes.wizard'

    field = fields.Many2one('ir.model.fields', string='Field', help="Select your field to copy",
            domain=[
                ('ttype', 'not in', FIELD_FILTER),
                '|',
                ('model', '=', 'product.product'),
                ('model', '=', 'product.template'),
            ], required=True)
    product_to = fields.Many2one('product.product', 'Product TO', help="Select your product to copy", required=True)
    lang = fields.Many2one('res.lang', string='Language', help="Select language to copy", required=True)
    result = fields.Text(string='Result', readonly=True)
    state = fields.Selection(selection=[
                    ('first', 'First'),
                    ('done', 'Done'),], string='State', default='first')

    @api.one
    def copy_attributes(self, data):
        """Copy attributes to field"""
        form = self = self.with_context(lang=self.lang)
        field = form.field
        product_to = form.product_to

        if len(data['active_ids']) > 1:
            raise Warning(_('Error!'), _('This wizard is available only one product'))

        for prod in data['active_ids']:
            value = prod.read([field.name])
            values = {field.name: value[0][field.name]}
            product_to.write(values)
        values = {
            'state':'done',
            'result': _('%s copy to: %s - %s') % (data['active_ids'], product_to.id, field.name),
        }
        self.write(values)
        return True

class product_attributes_fields_wizard(models.TransientModel):
    _name = 'product.attributes.fields.wizard'

    def open_attribute_fields(self, data):
        """Open Product Form with Attribute fields"""

        if len(data['active_ids']) > 1:
            raise Warning(_('Error!'), _('This wizard is available only one product'))

        products = data['active_ids']

        product = self.env['product.product'].browse(products[0])

        if not product.attribute_group_id:
            raise Warning(_('Error !'), _('Select a attribute group!.'))

        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
            
        mod_id = mod_obj.search([('name', '=', 'product_normal_action')])[0]
        res_id = mod_obj.read(mod_id, ['res_id'])['res_id']
        act_win = act_obj.read(res_id, [])
        act_win['domain'] = [('id', 'in', [product.id])]
        act_win['context'] = {'attribute_group_id':1}
        act_win['name'] = "%s" % (product.name)
        return act_win

