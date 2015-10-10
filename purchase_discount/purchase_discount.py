# -*- encoding: utf-8 -*-
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

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp

class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'
    
    @api.one
    @api.depends('price_unit', 'discount', 'taxes_id')
    def _amount_line(self):
        currency = self.order_id.pricelist_id.currency_id
        discount = self.discount or 0.0
        new_price_unit = self.price_unit * (1 - discount / 100.0)
        taxes = self.taxes_id.compute_all(new_price_unit, self.product_qty, self.product_id, self.order_id.partner_id)
        self.price_subtotal = currency.round(taxes['total'])

    discount = fields.Float(string='Discount (%)', digits=(16, 2), default=0.0)
    price_subtotal = fields.Float(compute='_amount_line', string='Subtotal', digits_compute=dp.get_precision('Account'))

    _sql_constraints = [
        ('discount_limit', 'CHECK (discount <= 100.0)', 'Discount must be lower than 100%.'),
    ]

class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    @api.one
    @api.depends('order_line.price_subtotal')
    def _amount_all(self):
        amount_taxed = amount_untaxed = 0.0
        currency = self.pricelist_id.currency_id
        for line in self.order_line:
            amount_untaxed += line.price_subtotal
            discount = line.discount or 0.0
            new_price_unit = line.price_unit * (1 - discount / 100.0)
            for c in line.taxes_id.compute_all(
                                         new_price_unit,
                                         currency.id,
                                         line.product_qty,
                                         line.product_id.id,
                                         self.partner_id)['taxes']:
                amount_taxed += c.get('amount', 0.0)
            self.amount_tax = currency.round(amount_taxed)
            self.amount_untaxed = currency.round(amount_untaxed)
            self.amount_total = (self.amount_untaxed + self.amount_tax)
    
    @api.model
    def _prepare_inv_line(self, account_id, order_line):
        result = super(purchase_order, self)._prepare_inv_line(account_id, order_line)
        result['discount'] = order_line.discount or 0.0
        return result

    amount_untaxed = fields.Float(compute='_amount_all', method=True,
        digits_compute=dp.get_precision('Account'),
        string='Untaxed Amount',
        store=True, multi="sums", help="The amount without tax")
    amount_tax = fields.Float(compute='_amount_all', method=True,
        digits_compute=dp.get_precision('Account'), string='Taxes',
        store=True, multi="sums", help="The tax amount")
    amount_total = fields.Float(compute='_amount_all', method=True,
            digits_compute=dp.get_precision('Account'), string='Total',
        store=True, multi="sums", help="The total amount")


# class stock_picking(models.Model):
#     _inherit = 'stock.picking'
    
#     @api.v7
#     def _invoice_line_hook(self, cr, uid, move_line, invoice_line_id):
#         if move_line.purchase_line_id:
#             line = {'discount': move_line.purchase_line_id.discount}
#             self.pool.get('account.invoice.line').write(cr,
#                                                         uid,
#                                                         [invoice_line_id],
#                                                         line)
#         return super(stock_picking, self)._invoice_line_hook(cr,
#                                                              uid,
#                                                              move_line,
#                                                              invoice_line_id)
#     @api.v7
#     def _get_discount_invoice(self, cursor, user, move_line):
#         if move_line.purchase_line_id:
#             return move_line.purchase_line_id.discount
#         return super(stock_picking, self)._get_discount_invoice(cursor, user, move_line)
    
#     @api.v7
#     def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id, invoice_vals, context=None):
#         invoice_vals = super(stock_picking, self)._prepare_invoice_line(cr, uid, group, picking, move_line, invoice_id, invoice_vals, context=context)
#         if picking.purchase_id:
#             if move_line.purchase_line_id:
#                 invoice_vals['account_analytic_id'] = self._get_account_analytic_invoice(cr, uid, picking, move_line)
#         return invoice_vals

class stock_move(models.Model):
    _inherit = 'stock.move'
         
#     @api.model
#     def _get_invoice_line_vals(self, move, partner, inv_type):
#         invoice_vals = super(stock_move, self)._get_invoice_line_vals(move, partner, inv_type)
#         if move.purchase_line_id:
#             invoice_vals['discount'] = move.purchase_line_id.discount
#             invoice_vals['account_analytic_id'] = move.picking_id.  (move.picking_id)
#         return invoice_vals
    
    @api.v7
    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
        invoice_vals = super(stock_move, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
        if move.purchase_line_id:
            invoice_vals['discount'] = move.purchase_line_id.discount
            invoice_vals['account_analytic_id'] = self.pool.get('stock.picking')._get_account_analytic_invoice(cr, uid, move.picking_id, move)
        return invoice_vals

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: