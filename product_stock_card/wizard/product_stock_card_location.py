# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Ecosoft Co., Ltd. (http://ecosoft.co.th).
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
from datetime import datetime

class product_stock_card_location(models.TransientModel):
    _name = 'product_stock.card.location'
   
    product_id = fields.Many2one('product.product', string='Product', domain=[('type', '!=', 'service')])
    location_id = fields.Many2one('stock.location', string='Location', domain=[('usage', '=', 'internal')])
    from_date = fields.Datetime(string='From Date')
    to_date = fields.Datetime(string='To Date')
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(product_stock_card_location, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if len(self._context.get('active_ids', [])) > 1:
            res['arch'] = res['arch'].replace('<button string="View Stock Card" name="open_stock_card" type="object" default_focus="1" class="oe_highlight"/>', '')
        return res
    
    @api.multi
    def open_stock_card(self):
        stock_card_location = self.read(['product_id', 'location_id', 'from_date', 'to_date'])
        domain = []
        if stock_card_location:
            if stock_card_location[0]['product_id']:
                product = stock_card_location[0]['product_id']
                ctx = {'search_default_product_id': product, 'default_product_id': product, }
            else:
                product = self._context.get('active_id', False)
                ctx = {'search_default_product_id': product, 'default_product_id': product, }

            if stock_card_location[0]['location_id']:
                ctx.update({'location': stock_card_location[0]['location_id'][0]})
                domain += ['|', ('location_id', '=', stock_card_location[0]['location_id'][0]), ('location_dest_id', '=', stock_card_location[0]['location_id'][0])]
            else:
                domain += [('type', 'not in', ('move', False))]

            if stock_card_location[0]['from_date']:
                start = datetime.strptime(stock_card_location[0]['from_date'], "%Y-%m-%d %H:%M:%S")
                domain += [('date', '>=', start.strftime('%Y-%m-%d'))]
            if stock_card_location[0]['to_date']:
                stop = datetime.strptime(stock_card_location[0]['to_date'], "%Y-%m-%d %H:%M:%S")
                domain += [('date', '<=', stop.strftime('%Y-%m-%d'))]

        return {
            'name': _('Stock Card By Location'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.stock.card',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'domain': domain,
        }
    
    @api.multi
    def print_stock_card(self):
        stock_card_location = self.read(['product_id', 'location_id', 'from_date', 'to_date'])
        domain = []
        ctx = self._context.copy()
        start = None
        stop = None
        parameters = {}
        product_id = False
        if stock_card_location:
            if stock_card_location[0]['product_id']:
                product_id = stock_card_location[0]['product_id'][0]
            else:
                product_id = self._context.get('active_id', False)

            if stock_card_location[0]['location_id']:
                location_id = stock_card_location[0]['location_id'][0]
                parameters.update({'location_id': location_id})
                ctx.update({'location': location_id})
                domain += ['|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)]
            else:
                domain += [('type', 'not in', ('move', False))]

            if stock_card_location[0]['from_date']:
                start = datetime.strptime(stock_card_location[0]['from_date'], "%Y-%m-%d %H:%M:%S")
                domain += [('date', '>=', start.strftime('%Y-%m-%d'))]
                parameters.update({'from_date': start.strftime('%Y-%m-%d')})

            if stock_card_location[0]['to_date']:
                stop = datetime.strptime(stock_card_location[0]['to_date'], "%Y-%m-%d %H:%M:%S")
                domain += [('date', '<=', stop.strftime('%Y-%m-%d'))]
                parameters.update({'to_date': stop.strftime('%Y-%m-%d')})

        data = self.read()[-1]
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'report.product.stock.card',
            'report_type': 'pdf',
            'context': ctx,
            'domain': domain,
            'datas': {
                'model': 'product.product',
                'id': product_id,
                'ids': [product_id],
                'form': data,
                'parameters': parameters
            }
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: