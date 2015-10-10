# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2011 Zikzakmedia S.L. (http://zikzakmedia.com) All Rights Reserved.
#                       Jesús Martín <jmartin@zikzakmedia.com>
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from openerp import tools
import unicodedata
import re
from openerp.exceptions import except_orm, Warning, RedirectWarning
            
def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return re.sub('[-\s]+', '-', value)

class product_attributes(models.Model):
    _name = 'product.attributes'
    _description = 'Product attributes for product OpenERP module'


#    def _get_fields_type(self, cr, uid, context=None):
#        cr.execute('select distinct ttype,ttype from ir_model_fields')
#        return cr.fetchall()

    @api.model
    def _get_fields_type(self):
        self.env.cr.execute('select distinct id, ttype, ttype from ir_model_fields')
        field_types1 = self.env.cr.fetchall()
        
        self.env.cr.execute('select distinct ttype,ttype from ir_model_fields')
        field_types = self.env.cr.fetchall()
        field_types_copy = field_types
        
        

        for types in field_types_copy:
            if not hasattr(fields, types[0]):
                field_types.remove(types)
        return field_types
    
    @api.model
    def create(self, vals):
        model_id = self.env['ir.model'].search([('model', '=', 'product.product')])[0]
        if 'selection' in vals:
            selection = vals['selection']
        else:
            selection = ''

        if 'relation' in vals:
            relation = vals['relation']
        else:
            relation = ''

        if 'relation_field' in vals:
            relation_field = vals['relation_field']
        else:
            relation_field = ''

        field_vals = {
            'field_description': vals['field_description'],
            'model_id': model_id.id,
            'model': 'product.product',
            'name': slugify(tools.ustr(vals['name'])),
            'ttype': vals['ttype'],
            'translate': vals['translate'],
            'required': vals['required'],
            'selection': selection,
            'relation': relation,
            'relation_field': relation_field,
            'state': 'manual',
        }
        field = self.env['ir.model.fields'].create(field_vals)
        vals['field_id'] = field.id 
        id = super(product_attributes, self).create(vals)
        return id

# Kittiu
#    def unlink(self, cr, uid, ids, context=None):
#        raise osv.except_osv(_('Alert !'), _('You can\'t delete this attribute'))
    
    @api.multi
    def write(self, vals):
        values = {}
        if 'sequence' in vals:
            values['sequence'] = vals['sequence']
        if 'required' in vals:
            values['required'] = vals['required']
        if 'translate' in vals:
            values['translate'] = vals['translate']

        return super(product_attributes, self).write(values)

    name = fields.Char(string='Name', required=True, default='x_')
    field_description = fields.Char(string='Field Label', required=True, translate=True)
    ttype = fields.Selection(selection='_get_fields_type', string='Field Type', required=True)
    field_id = fields.Many2one('ir.model.fields', 'product_id')
    translate = fields.Boolean(string='Translate')
    required = fields.Boolean(string='Required')
    selection = fields.Char(string='Selection Options', help="List of options for a selection field, "
        "specified as a Python expression defining a list of (key, label) pairs. "
        "For example: [('blue','Blue'),('yellow','Yellow')]")
    relation = fields.Char('Object Relation', help="For relationship fields, the technical name of the target model")
    relation_field = fields.Char(string='Relation Field', help="For one2many fields, the field on the target model that implement the opposite many2one relationship")
    sequence = fields.Integer(string='Sequence')

class product_attributes_group(models.Model):
    _name = 'product.attributes.group'
    _description = 'Product attributes group for product OpenERP module'
    
    @api.model
    def create_product_attributes_menu(self, vals):
        data_ids = self.env['ir.model.data'].search([('name', '=', 'menu_products'), ('module', '=', 'product')])
        
        if data_ids:
            product_attributes_menu_id = data_ids.res_id
            
        for attributes_group in self:
            menu_vals = {
                'name': attributes_group.name,
                'parent_id': product_attributes_menu_id,
                'icon': 'STOCK_JUSTIFY_FILL'
            }
            
            action_vals = {
                'name': attributes_group.name,
                'view_type':'form',
                'domain':"[('attribute_group_id', '=', %s)]" % attributes_group.id,
                'context': "{'attribute_group_id':%s}" % attributes_group.id,
                'res_model': 'product.product'
            }
            
            existing_menu_id = self.env['ir.ui.menu'].search([('name', '=', attributes_group.name)])
            
            if len(existing_menu_id) > 0:
                raise Warning(_('Error !'), _('There are other menu same this group. Please, use another name'))
                
            else:
                action_id = self.env['ir.actions.act_window'].create(action_vals)
                menu_vals['action'] = 'ir.actions.act_window,%s' % (action_id)
                menu_id = self.env['ir.ui.menu'].create(menu_vals)
                values = {
                    'action_id': action_id,
                    'menu_id': menu_id,
                }
                super(product_attributes_group, self).write(values)

    @api.model
    def create(self, vals):
        id = super(product_attributes_group, self).create(vals)
        self.create_product_attributes_menu(vals)
        return id
    
    @api.multi
    def write(self, vals):
        super(product_attributes_group, self).write(vals)
        for attributes_group in self:
            menu_vals = {
                'name': attributes_group.name,
            }
            
            action_vals = {
                'name': attributes_group.name,
            }
            
            result = self.env['ir.actions.act_window'].write(attributes_group.action_id.id, action_vals)
            result = result and self.env['ir.ui.menu'].write(attributes_group.menu_id.id, menu_vals)
            
            if not result:
                raise Warning(_('Error !'), _('Error ocurring during saving'))
        return True

    @api.multi
    def unlink(self):
        for attributes_group in self:
            result = attributes_group.action_id.unlink()
            result = result and attributes_group.menu_id.unlink()
            result = result and super(product_attributes_group, self).unlink()
            if not result:
                raise Warning(_('Error !'), _('Error ocurring during deleting'))
        return True

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, help='Attribute code, ex az09')
    product_att_ids = fields.Many2many('product.attributes', 'product_attributes_rel', 'product_attributes_group_id', 'product_attributes_id', string='Products Attributes')
    menu_id = fields.Many2one('ir.ui.menu', 'menu_id', readonly=True)
    action_id = fields.Many2one('ir.actions.act_window', 'action_id', readonly=True)

