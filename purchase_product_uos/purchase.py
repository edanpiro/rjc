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
import openerp.addons.decimal_precision as dp

class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    @api.model
    def _get_line_qty(self, line):
        if line.product_uos:
            return line.product_uos_qty or 0.0
        return line.product_qty
    
    @api.model
    def _get_line_uom(self, line):
        if line.product_uos:
            return line.product_uos.id
        return line.product_uom.id
    
    @api.model
    def _prepare_inv_line(self, account_id, order_line):
        res = super(purchase_order, self)._prepare_inv_line(account_id, order_line)
        uosqty = self._get_line_qty(order_line)
        uos_id = self._get_line_uom(order_line)
        pu = 0.0
        if uosqty:
            pu = round(order_line.price_unit * order_line.product_qty / uosqty,
                    self.env['decimal.precision'].precision_get('Product Price'))
        res.update({
            'price_unit': pu,
            'quantity': uosqty,
            'uos_id': uos_id
        })
        return res
     
    @api.model    
    def _prepare_order_line_move(self, order, order_line, picking_id, group_id):
        result = super(purchase_order, self)._prepare_order_line_move(order, order_line, picking_id, group_id)
        # If UOS, show UOS
        for res in result:
            res.update({'product_uos_qty': (order_line.product_uos and order_line.product_uos_qty) or order_line.product_qty,
                    'product_uos': (order_line.product_uos and order_line.product_uos.id) or order_line.product_uom.id})
        return result
        
class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"
    
    is_uos_product = fields.Boolean(string='Product has UOS?')
    product_uos_qty = fields.Float(string='Quantity (UoS)' , digits_compute=dp.get_precision('Product UoS'))
    product_uos = fields.Many2one('product.uom', string='Product UoS')
    price_uos_unit = fields.Float(string='Unit Price (UoS)', digits_compute=dp.get_precision('Product Price'))
    
    @api.v7
    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name='', price_unit=False, qty_uos=0, uos=False, state='draft', context=None): 
        
        print "onchange_product_id:::::::::::::::::;;78787887878787878:::::::::::::::::::::::"
        # Call super class method
        
        result = super(purchase_order_line, self).onchange_product_id(cr, uid, ids, pricelist_id, product_id, qty, uom,
            partner_id, date_order, fiscal_position_id, date_planned, name, price_unit, 'draft', context=context)
                
        if not product_id:
            return result
        
        # Based on sale.product_id_change, additional logic goes here,
        i_result = {}
        i_domain = {}
        i_warning = {}
        if result.get('value'):
            i_result = result['value']
        if result.get('domain'):
            i_domain = result['domain']
        if result.get('warning'):
            i_warning = result['warning']
            
        product_uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')
        product_obj = product_obj.browse(cr, uid, product_id)
        result = {}
        domain = {}
        warning = {}
        
        # Reset uom, if not in the same category.
        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}
        elif uos and not uom:  # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / (product_obj.uos_coeff > 0 and product_obj.uos_coeff or 1)
        elif uom:  # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            # KTU Start
            # result['product_uom'] = default_uom
            if not product_obj.uos_id:
                result['product_uom'] = uom
            else:  # If UOS always force to default_uom
                result['product_uom'] = default_uom
                uom = default_uom
            # KTU End
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                
        # Start KTU: Reset the price_unit one more time, in case that UOS is available (as uom will always set back to default)
        result['is_uos_product'] = False
        if product_obj.uos_id:
            result['is_uos_product'] = True
            product_pricelist = self.pool.get('product.pricelist')
            if pricelist_id:
                print "pricelist_id::::::::::::::::::",pricelist_id
                price = product_pricelist.price_get(cr, uid, [pricelist_id],
                        product_obj.id, qty or 1.0, partner_id or False, {'uom': uom, 'date': date_order})[pricelist_id]
                print "price:::::::::::;154::::::::",price
            else:
                price = product_obj.standard_price        
            result['price_unit'] = price
        # End KTU
        
        i_result.update(result)           
        i_domain.update(domain)
        i_warning.update(warning)
        
        return {'value': i_result, 'domain': i_domain, 'warning': i_warning}
    
    @api.v7
    def onchange_product_uos(self, cr, uid, ids, product_id, is_uos_product=False, qty=0, uom=False, qty_uos=0, uos=False):
        # Return when, no product
        if product_id:
            # Case 1: product is not UOS
            if not is_uos_product:
                return {'value': {'product_uos_qty': qty, 'product_uos': False}}
            else:            
                if uos == uom:
                    return {'value': {'product_uos_qty': qty}}
                else:
                    product = self.pool.get('product.product').browse(cr, uid, product_id)
                    uom = product.uom_id.id
                    uos = product.uos_id.id
                    qty = qty_uos / (product.uos_coeff > 0 and product.uos_coeff or 1)
                    # Problem with recursive conversion if qty is adjusted.
                    # return {'value': {'product_qty': qty, 'product_uom': uom}}
                    return {'value': {'product_uom': uom}}
        return {}
    
    @api.v7
    def onchange_price_uos_unit(self, cr, uid, ids, price_uos_unit, product_uos_qty, product_qty, context=None):
        if price_uos_unit and product_qty:
            price_unit = 0.0
            price_unit = float(price_uos_unit) * (float(product_uos_qty) / float(product_qty))
            return {'value': {'price_unit': price_unit}}
        return {}
    
    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default.update(price_uos_unit=0.0)
        return super(purchase_order_line, self).copy_data(default)    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: