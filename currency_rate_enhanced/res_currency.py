# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import time
from openerp import models, fields, api, _

class res_currency(models.Model):
    
    @api.multi
    @api.depends('rate', 'rate_sell')
    def _current_rate_sell(self):
        if 'date' in self._context:
            date = self._context['date']
        else:
            date = time.strftime('%Y-%m-%d')
        date = date or time.strftime('%Y-%m-%d')
        # Convert False values to None ...
        currency_rate_type = self._context.get('currency_rate_type_id') or None
        # ... and use 'is NULL' instead of '= some-id'.
        operator = '=' if currency_rate_type else 'is'
        
        self._cr.execute("SELECT currency_id, rate_sell FROM res_currency_rate WHERE currency_id = %s AND name <= %s AND currency_rate_type_id " + operator + " %s ORDER BY name desc LIMIT 1" , (self.id, date, currency_rate_type))
        if self._cr.rowcount:
            id, rate = self._cr.fetchall()[0]
            self.rate_sell = rate
        else:
            raise Warning(_('Error!'), _("No currency selling rate associated for currency %d for the given period" % (self.id)))
    
    _inherit = 'res.currency'

    type_ref_base = fields.Selection(selection=[
                          ('smaller', 'Smaller than base currency'),
                          ('bigger', 'Bigger than base currency'),
                      ], string='Type', required=True, default='smaller',
            help="""* If this currency is smaller, amount currency = amount base * rate * If this currency is bigger, amount currency = amount base / rate""")
    
    rate_sell = fields.Float(compute='_current_rate_sell', string='Current Selling Rate', digits=(12, 6),
                                help='The rate of the currency to the currency of rate 1.', default=1)


    # A complete override method
    # Added Selling / Buying Rates
    @api.model
    def _get_conversion_rate(self, from_currency, to_currency):
        ctx = dict(self._context)
        ctx.update({'currency_rate_type_id': ctx.get('currency_rate_type_from')})
        from_currency = self.with_context(ctx).browse(from_currency.id)

        ctx.update({'currency_rate_type_id': ctx.get('currency_rate_type_to')})
        to_currency = self.with_context(ctx).browse(to_currency.id)

        pricelist_type = self._context.get('pricelist_type', False) or 'sale'  # pricelist_type default to 'sale' and use buying rate
        to_currency_rate = 0.0
        from_currency_rate = 0.0
        # testing: Buying rate
        if pricelist_type == 'sale':
            if from_currency.rate == 0 or to_currency.rate == 0:
                date = self._context.get('date', time.strftime('%Y-%m-%d'))
                if from_currency.rate == 0:
                    currency_symbol = from_currency.symbol
                else:
                    currency_symbol = to_currency.symbol
                raise Warning(_('Error'), _('No buying rate found \n' \
                        'for the currency: %s \n' \
                        'at the date: %s') % (currency_symbol, date))
            to_currency_rate = to_currency.rate
            from_currency_rate = from_currency.rate
        # testing: Selling rate
        if pricelist_type == 'purchase':
            if from_currency.rate_sell == 0 or to_currency.rate_sell == 0:
                date = self._context.get('date', time.strftime('%Y-%m-%d'))
                if from_currency.rate == 0:
                    currency_symbol = from_currency.symbol
                else:
                    currency_symbol = to_currency.symbol
                raise Warning(_('Error'), _('No selling rate found \n' \
                        'for the currency: %s \n' \
                        'at the date: %s') % (currency_symbol, date))
            to_currency_rate = to_currency.rate_sell
            from_currency_rate = from_currency.rate_sell
        # testing: check Smaller/Bigger currency
        to_rate = to_currency.type_ref_base == 'bigger' and (1 / to_currency_rate) or to_currency_rate
        from_rate = from_currency.type_ref_base == 'bigger' and (1 / from_currency_rate) or from_currency_rate
        return to_rate / from_rate

class res_currency_rate(models.Model):
    _inherit = 'res.currency.rate'
    
    rate = fields.Float(string='Buying Rate', digits=(12, 6), help='The selling rate of the currency to the currency of rate 1')
    rate_sell = fields.Float(string='Selling Rate', digits=(12, 6), help='The purchase rate of the currency to the currency of rate 1', default=1)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
