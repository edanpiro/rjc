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

from openerp import models, fields, api, _
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class sale_advance_payment_inv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'
    
    @api.model
    def _get_advance_payment_method(self):
         res = [('None', 'None')]
         if self._context.get('active_model', False) == 'sale.order':
            sale_id = self._context.get('active_id', False)
            if sale_id:
                sale = self.env['sale.order'].browse(sale_id)
                # Advance option not available when, There are at least 1 non-cancelled invoice created
                num_valid_invoice = 0
                for i in sale.invoice_ids:
                   if i.state not in ['cancel']:
                        num_valid_invoice += 1
                if sale.order_policy == 'manual' and (num_valid_invoice or not self._context.get('advance_type', False)):
                    res.append(('all', 'Invoice the whole sales order'))
                    res.append(('lines', 'Some order lines'))
                if not num_valid_invoice and self._context.get('advance_type', False):
                    res.append(('percentage', 'Percentage'))
                    res.append(('fixed', 'Fixed price (deposit)'))
         
         return res
 
    advance_payment_method = fields.Selection('_get_advance_payment_method',default=lambda self: self._context.get('None', 'None'),
                                               string='What do you want to invoice?', required=True,
                                               help="""Use All to create the final invoice.
                                                 Use Percentage to invoice a percentage of the total amount.
                                                 Use Fixed Price to invoice a specific amound in advance.
                                                 Use Some Order Lines to invoice a selection of the sales order lines.""")
    
    amount = fields.Float(string='Amount', digits_compute=dp.get_precision('Account'), help="The amount to be invoiced in advance.")
    # Retention
    retention = fields.Float(string='Retention', digits_compute=dp.get_precision('Account'), default=lambda self: self._context.get('retention', False),
                                    help="The amount to be retained from invoices. The amount will be retained from this invoice onwards.")

    
    @api.multi
    def create_invoices(self):
        res = super(sale_advance_payment_inv, self).create_invoices()

        sale_obj = self.env['sale.order']

        # Update retention percentage
        sale_id = self._context.get('active_id', False)
        sale = sale_obj.browse(sale_id)
        
        if self.retention > 0.0:
            sale.write({'retention_percentage': self.retention})

        # Update advance and deposit
        if self.advance_payment_method in ['percentage', 'fixed']:
            advance_percent = 0.0
            advance_amount = 0.0
            amount_deposit = 0.0
            if sale_id:
               # sale = sale_obj.browse(sale_id)
                advance_type = self._context.get('advance_type', False)
                if advance_type:
                    if not sale.amount_net:
                        raise Warning(_('Amount Error!'),
                                _('This Sales Order has no values!'))
                if advance_type == 'advance':
                    # calculate the percentage of advancement
                    if self.advance_payment_method == 'percentage':
                        advance_percent = self.amount
                        advance_amount = (self.amount / 100) * sale.amount_net
                    elif self.advance_payment_method == 'fixed':
                        advance_amount = self.amount
                        advance_percent = (self.amount / sale.amount_net) * 100
                if advance_type == 'deposit':
                    # calculate the amount of deposit
                    if self.advance_payment_method == 'percentage':
                        amount_deposit = (self.amount / 100) * sale.amount_net
                    elif self.advance_payment_method == 'fixed':
                        amount_deposit = self.amount
                if advance_amount > sale.amount_net or amount_deposit > sale.amount_net:
                    raise Warning(_('Amount Error!'),
                            _('Amount > Sales Order amount!'))
                # write back to sale_order
                sale.write({'advance_percentage': advance_percent})
                sale.write({'amount_deposit': amount_deposit})

            # for retention, mark the invoice is_retention = True
            current_res = res.get('res_id') and self.env['account.invoice'].browse(res.get('res_id')) or False
            if sale.retention_percentage > 0.0 and current_res:
                current_res.write({'is_retention': True})
            # Update invoice
            if current_res:
                current_res.button_compute()

        return res

    # This is a complete overwrite method of sale/self/sale_make_invoice_advance (rev8852)
    # How ever we might not need to double check it, as it only relate to type = percentage and fixed amount.
    # Which is completely changed.
    @api.multi
    def _prepare_advance_invoice_vals(self):
        sale_obj = self.env['sale.order']
        ir_property_obj = self.env['ir.property']
        fiscal_obj = self.env['account.fiscal.position']
        inv_line_obj = self.env['account.invoice.line']
        sale_ids = self._context.get('active_ids', [])
        # testing
        advance_type = self._context.get('advance_type', False)
        advance_label = advance_type == 'deposit' and 'Deposit' or 'Advance'
        # -- testing

        result = []
        for sale in sale_obj.browse(sale_ids):
            val = inv_line_obj.product_id_change([], self.product_id.id,
                    False, partner_id=sale.partner_id.id, fposition_id=sale.fiscal_position.id)
            res = val['value']

            # testing: determine and check advance customer account
            if not self.product_id.id:
                if advance_type == 'advance':
                # Case Advance
                    prop = ir_property_obj.get('property_account_advance_customer', 'res.partner')
                   # prop_id = prop and prop.id or False
                    account_id = fiscal_obj.map_account(prop)#sale.fiscal_position or False, prop_id)
                    if not account_id:
                        raise Warning(_('Configuration Error!'),
                                _('There is no advance customer account defined as global property.'))
                    res['account_id'] = account_id.id
                # Case Deposit
                if advance_type == 'deposit':
                    prop = ir_property_obj.get('property_account_deposit_customer', 'res.partner')
                    #prop_id = prop and prop.id or False
                    account_id = fiscal_obj.map_account(prop)#sale.fiscal_position or False, prop_id)
                    if not account_id:
                        raise Warning(_('Configuration Error!'),
                                _('There is no deposit customer account defined as global property.'))
                    res['account_id'] = account_id.id

            # determine invoice amount
            if self.amount <= 0.00:
                raise Warning(_('Incorrect Data'),
                    _('The value of %s Amount must be positive.') % (advance_label))
            if self.advance_payment_method == 'percentage':
                # testing: Use net amount before Tax!!! Then, it should have tax
                inv_amount = sale.amount_net * self.amount / 100
                if not res.get('name'):
                    res['name'] = _("%s of %s %%") % (advance_label, self.amount)
                # -- testing
            else:
                inv_amount = self.amount
                if not res.get('name'):
                    #TODO: should find a way to call formatLang() from rml_parse
                    symbol = sale.pricelist_id.currency_id.symbol
                    if sale.pricelist_id.currency_id.position == 'after':
                        res['name'] = _("%s of %s %s") % (advance_label, inv_amount, symbol)
                    else:
                        res['name'] = _("%s of %s %s") % (advance_label, symbol, inv_amount)

            # create the invoice
            inv_line_values = {
                'name': res.get('name'),
                'origin': sale.name,
                'user_id': sale.user_id.id,
                'account_id': res['account_id'],
                'price_unit': inv_amount,
                'quantity': self.qtty or 1.0,
                'discount': False,
                'uos_id': res.get('uos_id', False),
                'product_id': self.product_id.id,
                'invoice_line_tax_id': [(6, 0, [x.id for x in sale.order_line[0].tax_id])],
                'account_analytic_id': sale.project_id.id or False,
                # testing
                'is_advance': advance_type == 'advance' and True or False,
                'is_deposit': advance_type == 'deposit' and True or False
                # -- testing
            }
            inv_values = {
                'name': sale.client_order_ref or sale.name,
                'origin': sale.name,
                'user_id': sale.user_id.id,
                'type': 'out_invoice',
                'reference': False,
                'account_id': sale.partner_id.property_account_receivable.id,
                'partner_id': sale.partner_invoice_id.id,
                'invoice_line': [(0, 0, inv_line_values)],
                'currency_id': sale.pricelist_id.currency_id.id,
                'comment': '',
                'payment_term': sale.payment_term.id,
                'fiscal_position': sale.fiscal_position.id or sale.partner_id.property_account_position.id,
                # testing
                'is_advance': advance_type == 'advance' and True or False,
                'is_deposit': advance_type == 'deposit' and True or False,
            }
            result.append((sale.id, inv_values))
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
