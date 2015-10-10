# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2010-2011 Akretion (www.akretion.com). All Rights Reserved
#    @author Sebatien Beau <sebastien.beau@akretion.com>
#    @author Raphaël Valyi <raphael.valyi@akretion.com>
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#    update to use a single "Generate/Update" button & price computation code
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

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
# Lib to eval python code with security
from openerp.tools.safe_eval import safe_eval

import logging
_logger = logging.getLogger(__name__)

#
# Dimensions Definition
#
class product_variant_dimension_type(models.Model):
    _name = "product.variant.dimension.type"
    _description = "Dimension Type"

    description = fields.Char(string='Description', size=64, translate=True)
    name = fields.Char(string='Dimension', size=64, required=True)
    sequence = fields.Integer(string='Sequence', help="The product 'variants' code will use this to order the dimension values")
    option_ids = fields.One2many('product.variant.dimension.option', 'dimension_id', string='Dimension Options')
    product_tmpl_id = fields.Many2many('product.template', 'product_template_dimension_rel', 'dimension_id', 'template_id', string='Product Template')
    allow_custom_value = fields.Boolean(string='Allow Custom Value', help="If true, custom values can be entered in the product configurator")
    mandatory_dimension = fields.Boolean(string='Mandatory Dimension', default=1, help="If false, variant products will be created with and without this dimension")

    _order = "sequence, name"
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=None):
        if not self._context.get('product_tmpl_id', False):
            args = None
        return super(product_variant_dimension_type, self).name_search('', args=args, operator=operator, limit=limit)

class product_variant_dimension_option(models.Model):
    _name = "product.variant.dimension.option"
    _description = "Dimension Option"
    
    @api.model
    def _get_dimension_values(self):
        return self.env['product.variant.dimension.value'].search([('dimension_id', 'in', self.ids)])

    name = fields.Char(string='Name', size=64, required=True)
    code = fields.Char(string='Code', size=64)
    sequence = fields.Integer(string='Sequence')
    dimension_id = fields.Many2one('product.variant.dimension.type', string='Dimension Type', ondelete='cascade')

    _order = "dimension_id, sequence, name"

class product_variant_dimension_value(models.Model):
    _name = "product.variant.dimension.value"
    _description = "Dimension Value"
    
    @api.multi
    def unlink(self):
        for value in self:
            if value.product_ids:
                product_list = '\n    - ' + '\n    - '.join([product.name for product in value.product_ids])
                raise Warning(_('Dimension value can not be removed'), _("The value %s is used by the products : %s \n Please remove these products before removing the value." % (value.option_id.name, product_list)))
        return super(product_variant_dimension_value, self).unlink()
    
    # @api.model
    # def 
    # _get_values_from_types(self):
    #     return self.env['product.variant.dimension.value'].search([('dimension_id', 'in', self.id)])
    
    # @api.one
    # def _get_values_from_options(self):
    #     return self.env['product.variant.dimension.value'].search([('option_id', 'in', self.ids)])

    option_id = fields.Many2one('product.variant.dimension.option', string='Option', required=True)
    name = fields.Char(related='option_id.name', string="Dimension value", readonly=True)
    sequence = fields.Integer(string='Sequence')
    price_extra = fields.Float(string='Sale Price Extra', digits_compute=dp.get_precision('Sale Price'))
    price_margin = fields.Float(string='Sale Price Margin', digits_compute=dp.get_precision('Sale Price'))
    cost_price_extra = fields.Float(string='Cost Price Extra', digits_compute=dp.get_precision('Purchase Price'))
    dimension_id = fields.Many2one(related='option_id.dimension_id', string="Dimension Type", readonly=True, store=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', ondelete='cascade')
    dimension_sequence = fields.Integer(related='dimension_id.sequence', string="Related Dimension Sequence",  # used for ordering purposes in the "variants"
                                            store=True)
    product_ids = fields.Many2many('product.product', 'product_product_dimension_rel', 'dimension_id', 'product_id', string='Variant', readonly=True)
    active = fields.Boolean(string='Active?', help="If false, this value will be not use anymore for generating variant", default=True)


    _sql_constraints = [ ('opt_dim_tmpl_uniq', 'UNIQUE(option_id, dimension_id, product_tmpl_id)',
                _('The combination option and dimension type already exists for this product template !')), ]

    _order = "dimension_sequence, dimension_id, sequence, option_id"

class product_template(models.Model):
    _inherit = "product.template"

    name = fields.Char('Name', translate=True, select=True)
    dimension_type_ids = fields.Many2many('product.variant.dimension.type', 'product_template_dimension_rel', 'template_id', 'dimension_id', string='Dimension Types')
    value_ids = fields.One2many('product.variant.dimension.value', 'product_tmpl_id', string='Dimension Values')
    variant_ids = fields.One2many('product.product', 'product_tmpl_id', string='Variants', copy=False)
    variant_model_name = fields.Char(string='Variant Model Name', required=True, default='[_o.dimension_id.name_] - [_o.option_id.name_]',
                                     help='[_o.dimension_id.name_] will be replaced by the name of the dimension and [_o.option_id.code_] by the code of the option. Example of Variant Model Name : "[_o.dimension_id.name_] - [_o.option_id.code_]"')
    variant_model_name_separator = fields.Char(string='Variant Model Name Separator', default=' - ', help='Add a separator between the elements of the variant name')
    code_generator = fields.Char(string='Code Generator', default="[_'-'.join([x.option_id.name for x in o.dimension_value_ids] or ['CONF'])_]", help='enter the model for the product code, all parameter between [_o.my_field_] will be replace by the product field. Example product_code model : prefix_[_o.variants_]_suffixe ==> result : prefix_2S2T_suffix')
    is_multi_variants = fields.Boolean(string='Is Multi Variants?')
    variant_track_production = fields.Boolean(string='Track Production Lots on variants ?')
    variant_track_incoming = fields.Boolean(string='Track Incoming Lots on variants ?')
    variant_track_outgoing = fields.Boolean(string='Track Outgoing Lots on variants ?')
    do_not_update_variant = fields.Boolean(string="Don't Update Variant")
    do_not_generate_new_variant = fields.Boolean(string="Don't Generate New Variant")
    
    @api.multi
    def unlink(self):
        if self._context and self._context.get('unlink_from_product_product', False):
            for template in self:
                if not template.is_multi_variants:
                    super(product_template, self).unlink()
        return True
    
    @api.multi
    def add_all_option(self):
        # Reactive all unactive values
        value_obj = self.env['product.variant.dimension.value']
        for template in self:
            values_ids = value_obj.search([['product_tmpl_id', '=', template.id], '|', ['active', '=', False], ['active', '=', True]])
            values_ids.write({'active':True})
            existing_option_ids = [value.option_id.id for value in values_ids]
            vals = {'value_ids' : []}
            for dim in template.dimension_type_ids:
                for option in dim.option_ids:
                    if not option.id in existing_option_ids:
                        vals['value_ids'] += [[0, 0, {'option_id': option.id}]]
            template.write(vals)
        return True
    
    @api.one
    def get_products_from_product_template(self):
        product_tmpl = self.read(['variant_ids'])
        return [id for vals in product_tmpl for id in vals['variant_ids']]
    
    @api.one
    def copy_translations(self, old_id, new_id):
        # avoid recursion through already copied records in case of circular relationship
        seen_map = self._context.setdefault('__copy_translations_seen', {})
        if old_id in seen_map.setdefault(self._name, []):
            return
        seen_map[self._name].append(old_id)
        return super(product_template, self).copy_translations(old_id, new_id)
    
    @api.multi
    def _create_variant_list(self, vals):
        def cartesian_product(args):
            if len(args) == 1: return [x and [x] or [] for x in args[0]]
            return [(i and [i] or []) + j for j in cartesian_product(args[1:]) for i in args[0]]
        return cartesian_product(vals)
    
    @api.multi
    def button_generate_variants(self):
        variants_obj = self.env['product.product']

        for product_temp in self:
            # for temp_type in product_temp.dimension_type_ids:
            #    temp_val_list.append([temp_type_value.id for temp_type_value in temp_type.value_ids] + (not temp_type.mandatory_dimension and [None] or []))
                # TODO c'est quoi ça??
                # if last dimension_type has no dimension_value, we ignore it
            #    if not temp_val_list[-1]:
            #        temp_val_list.pop()
            res = {}
            temp_val_list = []
            for value in product_temp.value_ids:
                if res.get(value.dimension_id, False):
                    res[value.dimension_id] += [value.id]
                else:
                    res[value.dimension_id] = [value.id]
            for dim in res:
                temp_val_list += [res[dim] + (not dim.mandatory_dimension and [None] or [])]

            existing_product_ids = variants_obj.search([('product_tmpl_id', '=', product_temp.id)])
            created_product_ids = []
            if temp_val_list and not product_temp.do_not_generate_new_variant:
                list_of_variants = self._create_variant_list(temp_val_list)
                existing_product_dim_value = existing_product_ids.read(['dimension_value_ids'])
                list_of_variants_existing = [x['dimension_value_ids'] for x in existing_product_dim_value]
                for x in list_of_variants_existing:
                    x.sort()
                for x in list_of_variants:
                    x.sort()
                list_of_variants_to_create = [x for x in list_of_variants if not x in list_of_variants_existing]

                _logger.debug("variant existing : %s, variant to create : %s", len(list_of_variants_existing), len(list_of_variants_to_create))
                count = 0
                for variant in list_of_variants_to_create:
                    count += 1

                    vals = {}
                    vals['track_production'] = product_temp.variant_track_production
                    vals['track_incoming'] = product_temp.variant_track_incoming
                    vals['track_outgoing'] = product_temp.variant_track_outgoing
                    vals['product_tmpl_id'] = product_temp.id
                    vals['dimension_value_ids'] = [(6, 0, variant)]

                    self.cr.execute("SAVEPOINT pre_variant_save")
                    try:
                        created_product_ids.append(variants_obj.create(vals, {'generate_from_template' : True}))
                        if count % 50 == 0:
                            _logger.debug("product created : %s", count)
                    except Exception, e:
                        _logger.error("Error creating product variant: %s", e, exc_info=True)
                        _logger.debug("Values used to attempt creation of product variant: %s", vals)
                        self.cr.execute("ROLLBACK TO SAVEPOINT pre_variant_save")
                    self.cr.execute("RELEASE SAVEPOINT pre_variant_save")

                _logger.debug("product created : %s", count)

            if not product_temp.do_not_update_variant:
                product_ids = existing_product_ids + created_product_ids
            else:
                product_ids = created_product_ids

            # FIRST, Generate/Update variant names ('variants' field)
            _logger.debug("Starting to generate/update variant names...")
            product_ids.build_variants_name()
            _logger.debug("End of the generation/update of variant names.")
            # SECOND, Generate/Update product codes and properties (we may need variants name for that)
            _logger.debug("Starting to generate/update product codes and properties...")
            product_ids.build_product_code_and_properties()
            _logger.debug("End of the generation/update of product codes and properties.")
            # THIRD, Generate/Update product names (we may need variants name for that)
            _logger.debug("Starting to generate/update product names...")
            product_ids.build_product_name()
            _logger.debug("End of generation/update of product names.")
            _logger.debug("Starting to updating prices ...")
            product_ids.update_variant_price()
            _logger.debug("End of updating prices.")
        return True

class product_product(models.Model):
    _inherit = "product.product"
    
#     @api.v7
#     def init(self, cr):
#         # For the first installation if you already have product in your database the name of the existing product will be empty, so we fill it
#         cr.execute("update product_product set name=name_template where name is null;")
#         return True
    
    @api.multi
    def unlink(self):
        self.with_context(unlink_from_product_product=True)
        return super(product_template, self).unlink()
    
    @api.model
    def build_product_name(self):
        return self.build_product_field('name')
    
    @api.model
    def build_product_field(self, field):
        def get_description_sale(product):
            return self.parse(product, product.product_tmpl_id.description_sale)

        def get_name(product):
            return (product.product_tmpl_id.name or '') + ' ' + (product.variants or '')

        self._context['is_multi_variants'] = True
        obj_lang = self.env['res.lang']
        lang_ids = obj_lang.search([('translatable', '=', True)])
        lang_code = [x['code'] for x in obj_lang.read(lang_ids, ['code'])]
        for code in lang_code:
            self._context['lang'] = code
            for product in self:
                new_field_value = eval("get_" + field + "(product)")  # TODO convert to safe_eval
                cur_field_value = safe_eval("product." + field, {'product': product})
                if new_field_value != cur_field_value:
                    product.write({field: new_field_value})
        return True
    
    @api.model
    def parse(self, o, text):
        if not text:
            return ''
        vals = text.split('[_')
        description = ''
        for val in vals:
            if '_]' in val:
                sub_val = val.split('_]')
                description += (safe_eval(sub_val[0], {'o' :o, 'context':self._context}) or '') + sub_val[1]
            else:
                description += val
        return description
    
    @api.model
    def generate_product_code(self, product_obj, code_generator):
        '''I wrote this stupid function to be able to inherit it in a custom module !'''
        return self.parse(product_obj, code_generator)
    
    @api.model
    def build_product_code_and_properties(self):
        for product in self:
            new_default_code = self.generate_product_code(product, product.product_tmpl_id.code_generator)
            current_values = {
                'default_code': product.default_code,
                'track_production': product.track_production,
                'track_outgoing': product.track_outgoing,
                'track_incoming': product.track_incoming,
            }
            new_values = {
                'default_code': new_default_code,
                'track_production': product.product_tmpl_id.variant_track_production,
                'track_outgoing': product.product_tmpl_id.variant_track_outgoing,
                'track_incoming': product.product_tmpl_id.variant_track_incoming,
            }
            if new_values != current_values:
                product.write(new_values)
        return True
    
    @api.model
    def product_ids_variant_changed(self, res):
        '''it's a hook for product_variant_multi advanced'''
        return True
    
    @api.multi
    def generate_variant_name(self, product_id):
        '''Do the generation of the variant name in a dedicated function, so that we can
        inherit this function to hack the code generation'''
        product = self.browse(product_id)
        model = product.variant_model_name
        r = map(lambda dim: [dim.dimension_id.sequence , self.parse(dim, model)], product.dimension_value_ids)
        r.sort()
        r = [x[1] for x in r]
        new_variant_name = (product.variant_model_name_separator or '').join(r)
        return new_variant_name
    
    @api.multi
    def build_variants_name(self):
        for product in self:
            new_variant_name = self.generate_variant_name(product.id)
            if new_variant_name != product.variants:
                product.write({'variants': new_variant_name})
        return True
    
    @api.multi
    def update_variant_price(self):
        for product in self:
            extra_prices = {
                'cost_price_extra': 0,
                'price_extra': 0,
            }
            for var_obj in product.dimension_value_ids:
                extra_prices['cost_price_extra'] += var_obj.cost_price_extra
                extra_prices['price_extra'] += var_obj.price_extra
            product.write(extra_prices)
        return True
    
    @api.multi
    def _check_dimension_values(self):  # TODO: check that all dimension_types of the product_template have a corresponding dimension_value ??
        for product in self:
            for value in product.dimension_value_ids:
                buffer.append(value.dimension_id)
            unique_set = set(buffer)
            if len(unique_set) != len(buffer):
                raise Warning(_('Constraint error :'), _("On product '%s', there are several dimension values for the same dimension type.") % product.name)
        return True
    
    @api.multi
    def compute_product_dimension_extra_price(self, product_id, product_price_extra=False, dim_price_margin=False, dim_price_extra=False):
        dimension_extra = 0.0
        for dim in self.dimension_value_ids:
            if product_price_extra and dim_price_margin and dim_price_extra:
                dimension_extra += safe_eval('product.' + product_price_extra, {'product': self}) * safe_eval('dim.' + dim_price_margin, {'dim': dim}) + safe_eval('dim.' + dim_price_extra, {'dim': dim})
            elif not product_price_extra and not dim_price_margin and dim_price_extra:
                dimension_extra += safe_eval('dim.' + dim_price_extra, {'dim': dim})
            elif product_price_extra and dim_price_margin and not dim_price_extra:
                dimension_extra += safe_eval('product.' + product_price_extra, {'product': self}) * safe_eval('dim.' + dim_price_margin, {'dim': dim})
            elif product_price_extra and not dim_price_margin and dim_price_extra:
                dimension_extra += safe_eval('product.' + product_price_extra, {'product': self}) + safe_eval('dim.' + dim_price_extra, {'dim': dim})

        if 'uom' in self._context:
            product_uom_obj = self.env['product.uom']
            uom = self.uos_id or self.uom_id
            dimension_extra = product_uom_obj._compute_price(uom.id, dimension_extra, self._context['uom'])
        return dimension_extra
    
    @api.model
    def compute_dimension_extra_price(self, result, product_price_extra=False, dim_price_margin=False, dim_price_extra=False):
        for product in self:
            dimension_extra = self.compute_product_dimension_extra_price(product_price_extra=product_price_extra, dim_price_margin=dim_price_margin, dim_price_extra=dim_price_extra)
            result[product.id] += dimension_extra
        return result
    
    @api.v7
    def price_get(self, cr, uid, ids, ptype='list_price', context=None):
        if context is None:
            context = {}
        result = super(product_template, self).price_get(cr, uid, ids, ptype, context=context)
        if ptype == 'list_price':  # TODO check if the price_margin on the dimension is very usefull, maybe we will remove it
            result = self.compute_dimension_extra_price(cr, uid, ids, result, product_price_extra='price_extra', dim_price_margin='price_margin', dim_price_extra='price_extra', context=context)
        elif ptype == 'standard_price':
            result = self.compute_dimension_extra_price(cr, uid, ids, result, product_price_extra='cost_price_extra', dim_price_extra='cost_price_extra', context=context)
        return result
    
    @api.v7
    def _product_lst_price(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = super(product_template, self)._product_lst_price(cr, uid, ids, name, arg, context=context)
        result = self.compute_dimension_extra_price(cr, uid, ids, result, product_price_extra='price_extra', dim_price_margin='price_margin', dim_price_extra='price_extra', context=context)
        return result
    
    @api.one
    @api.depends('weight', 'additional_weight', 'weight_net', 'additional_weight_net', 'volume', 'additional_volume')
    def _product_compute_weight_volume(self):
        self.total_weight = self.weight + self.additional_weight
        self.total_weight_net = self.weight_net + self.additional_weight_net
        self.total_volume = self.volume + self.additional_volume

#     name = fields.Char(string='Name', translate=True, select=True)
    variants = fields.Char(string='Variants')
    dimension_value_ids = fields.Many2many('product.variant.dimension.value', 'product_product_dimension_rel', 'product_id', 'dimension_id', string='Dimensions', domain="[('product_tmpl_id','=',product_tmpl_id)]")
    cost_price_extra = fields.Float(string='Purchase Extra Cost', digits_compute=dp.get_precision('Purchase Price'))
    lst_price = fields.Float(compute='_product_lst_price', string='List Price', digits_compute=dp.get_precision('Sale Price'))
    # the way the weight are implemented are not clean at all, we should redesign the module product form the addons in order to get something correclty.
    # indeed some field of the template have to be overwrited like weight, name, weight_net, volume.
    # in order to have a consitent api we should use the same field for getting the weight, now we have to use "weight" or "total_weight" not clean at all with external syncronization
    total_weight = fields.Float(compute='_product_compute_weight_volume', string='Gross weight', help="The gross weight in Kg.", multi='weight_volume')
    total_weight_net = fields.Float(compute='_product_compute_weight_volume', string='Net weight', help="The net weight in Kg.", multi='weight_volume')
    total_volume = fields.Float(compute='_product_compute_weight_volume', string='Volume', help="The volume in m3.", multi='weight_volume')
    additional_weight = fields.Float(string='Additional Gross weight', help="The additional gross weight in Kg.")
    additional_weight_net = fields.Float(string='Additional Net weight', help="The additional net weight in Kg.")
    additional_volume = fields.Float(string='Additional Volume', help="The additional volume in Kg.")

    _constraints = [
        (_check_dimension_values, 'Error msg in raise', ['dimension_value_ids']),
    ]

