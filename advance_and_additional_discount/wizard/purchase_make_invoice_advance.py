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
import openerp.addons.decimal_precision as dp

class purchase_advance_payment_inv(models.TransientModel):
    _name = "purchase.advance.payment.inv"
    _description = "Purchase Advance Payment Invoice"

    advance_payment_method = fields.Selection(
                              selection=[('percentage', 'Percentage'), ('fixed', 'Fixed price (deposit)')],
                              string='What do you want to invoice?', 
                              help="""Use Percentage to invoice a percentage of the total amount.
                                    Use Fixed Price to invoice a specific amount in advance.""")
    amount = fields.Float(string='Amount', digits_compute=dp.get_precision('Account'), help="The amount to be invoiced in advance.", default=0.0)
    
    @api.multi
    def _prepare_advance_invoice_vals(self):
        purchase_obj = self.env['purchase.order']
        ir_property_obj = self.env['ir.property']
        fiscal_obj = self.env['account.fiscal.position']
        purchase_ids = self._context.get('active_ids', [])
        advance_type = self._context.get('advance_type', False)
        advance_label = advance_type == 'deposit' and 'Deposit' or 'Advance'

        result = []
        for purchase in purchase_obj.browse(purchase_ids):
            res = {}
            # Case Advance
            if advance_type == 'advance':
                prop = ir_property_obj.get('property_account_advance_supplier', 'res.partner')
               # prop_id = prop and prop.id or False
                account_id = fiscal_obj.map_account(prop)#purchase.fiscal_position or False, prop_id)
                if not account_id:
                    raise Warning(_('Configuration Error!'),
                            _('There is no advance supplier account defined as global property.'))
                res['account_id'] = account_id.id
            # Case Deposit
            if advance_type == 'deposit':
                prop = ir_property_obj.get('property_account_deposit_supplier', 'res.partner')
                #prop_id = prop and prop.id or False
                account_id = fiscal_obj.map_account(prop)#purchase.fiscal_position or False, prop_id)
                if not account_id:
                    raise Warning(_('Configuration Error!'),
                            _('There is no deposit customer account defined as global property.'))
                res['account_id'] = account_id.id

            # determine invoice amount
            if self.amount <= 0.00:
                raise Warning(_('Incorrect Data'),
                    _('The value of %s Amount must be positive.') % (advance_label))
            if self.advance_payment_method == 'percentage':
                inv_amount = purchase.amount_net * self.amount / 100
                if not res.get('name'):
                    res['name'] = _("%s of %s %%") % (advance_label, self.amount)

            else:
                inv_amount = self.amount
                if not res.get('name'):
                    #TODO: should find a way to call formatLang() from rml_parse
                    symbol = purchase.pricelist_id.currency_id.symbol
                    if purchase.pricelist_id.currency_id.position == 'after':
                        res['name'] = _("%s of %s %s") % (advance_label, inv_amount, symbol)
                    else:
                        res['name'] = _("%s of %s %s") % (advance_label, symbol, inv_amount)

            # create the invoice
            inv_line_values = {
                'name': res.get('name'),
                'origin': purchase.name,
                'account_id': res['account_id'],
                'price_unit': inv_amount,
                'quantity': 1.0,
                'discount': False,
                'uos_id': False,
                'product_id': False,
                'invoice_line_tax_id': [(6, 0, [x.id for x in purchase.order_line[0].taxes_id])],
                'account_analytic_id': False,
                'is_advance': advance_type == 'advance' and True or False,
                'is_deposit': advance_type == 'deposit' and True or False
            }
            inv_values = {
                'name': purchase.partner_ref or purchase.name,
                'origin': purchase.name,
                'type': 'in_invoice',
                'reference': False,
                'account_id': purchase.partner_id.property_account_payable.id,
                'partner_id': purchase.partner_id.id,
                'invoice_line': [(0, 0, inv_line_values)],
                'currency_id': purchase.pricelist_id.currency_id.id,
                'comment': '',
                'payment_term': purchase.payment_term_id.id,
                'fiscal_position': purchase.fiscal_position.id or purchase.partner_id.property_account_position.id,
                'is_advance': advance_type == 'advance' and True or False,
                'is_deposit': advance_type == 'deposit' and True or False
            }
            result.append((purchase, inv_values))
        return result
    
    @api.multi
    def _create_invoices(self, inv_values, purchase_id):
       # self.context['type'] = 'in_invoice'
	self = self.with_context(type='in_invoice')
        inv_obj = self.env['account.invoice']
        inv_id = inv_obj.create(inv_values)
        inv_id.button_reset_taxes()
        # add the invoice to the purchase order's invoices
        purchase_id.write({'invoice_ids': [(4, inv_id.id)]})
        return inv_id.id
   
    @api.multi
    def create_invoices(self):
        """ create invoices for the active purchase orders """
        purhcase_obj = self.env['purchase.order']
        purchase_id = self._context.get('active_id', False)

        inv_ids = []
        for purhcase_id, inv_values in self._prepare_advance_invoice_vals():
            inv_ids.append(self._create_invoices(inv_values, purhcase_id))

        # Update advance and deposit
        if self.advance_payment_method in ['percentage', 'fixed']:
            advance_percent = 0.0
            advance_amount = 0.0
            amount_deposit = 0.0
            if purchase_id:
                purchase = purhcase_obj.browse(purchase_id)
                advance_type = self._context.get('advance_type', False)
                if advance_type == 'advance':
                    # calculate the percentage of advancement
                    if self.advance_payment_method == 'percentage':
                        advance_percent = self.amount
                        advance_amount = (self.amount / 100) * purchase.amount_net
                    elif self.advance_payment_method == 'fixed':
                        advance_amount = self.amount
                        advance_percent = (self.amount / purchase.amount_net) * 100
                if advance_type == 'deposit':
                    # calculate the amount of deposit
                    if self.advance_payment_method == 'percentage':
                        amount_deposit = (self.amount / 100) * purchase.amount_net
                    elif self.advance_payment_method == 'fixed':
                        amount_deposit = self.amount
                if advance_amount > purchase.amount_net or amount_deposit > purchase.amount_net:
                    raise Warning(_('Amount Error!'),
                            _('Amount > Purchase Order amount!'))
                # write back to sale_order
                purchase.write({'advance_percentage': advance_percent})
                purchase.write({'amount_deposit': amount_deposit})

        if self._context.get('open_invoices', False):
            return self.open_invoices(inv_ids)
        return {'type': 'ir.actions.act_window_close'}
    
    @api.multi
    def open_invoices(self, invoice_ids):
        """ open a view on one of the given invoice_ids """
        ir_model_data = self.env['ir.model.data']
        form_res = ir_model_data.get_object_reference('account', 'invoice_supplier_form')
        form_id = form_res and form_res[1] or False
        tree_res = ir_model_data.get_object_reference('account', 'invoice_tree')
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Advance Invoice'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'account.invoice',
            'res_id': invoice_ids[0],
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'tree')],
            'context': "{'type': 'in_invoice'}",
            'type': 'ir.actions.act_window',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
