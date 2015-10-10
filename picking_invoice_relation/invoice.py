# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2011 Camptocamp (<http://www.camptocamp.com>).
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

class account_invoice(models.Model):
    _inherit = 'account.invoice'

    # FIXME -this is not used, because info is in account_invoice.name
    @api.one
    @api.depends('sale_order_ids')
    def _client_order_refs(self):
        client_ref = '' 
        for ref in self.sale_order_ids:
            if ref.client_order_ref:
                if client_ref:
                    client_ref += '; '
                client_ref += ref.client_order_ref
        self.client_order_refs = client_ref 

    picking_ids = fields.Many2many('stock.picking', 'picking_invoice_rel', 'invoice_id', 'picking_id', string='Pickings', copy=False)
    sale_order_ids = fields.Many2many('sale.order', 'sale_order_invoice_rel', 'invoice_id', 'order_id', string='Sale Orders', readonly=True, help='This is the list of sale orders linked to this invoice.', copy=False)
    purchase_order_ids = fields.Many2many('purchase.order', 'purchase_invoice_rel', 'invoice_id', 'purchase_id', string='Purchase Orders', readonly=True, help="This is the list of purchase orders linked to this invoice. ")
    client_order_refs = fields.Char(compute='_client_order_refs', string="Client Sale Orders Ref")
    invoice_id_ref = fields.Many2one('account.invoice', string='Invoice Ref', readonly=True, copy=False)
    invoice_refund_refs = fields.One2many('account.invoice', 'invoice_id_ref', string='Refunded Invoice', readonly=True)
    
    @api.multi
    def write(self, vals):
        res = super(account_invoice, self).write(vals)
        # On create invoice, if picking associate with it has reference to another picking,
        # get the invoice associate with that picking.
        for invoice in self:
            if not invoice.invoice_id_ref:
                if invoice.picking_ids and invoice.picking_ids[0]:
                    if invoice.picking_ids[0].picking_id_ref:
                        if invoice.picking_ids[0].picking_id_ref.invoice_ids and invoice.picking_ids[0].picking_id_ref.invoice_ids[0]:
                            invoice_id_ref = invoice.picking_ids[0].picking_id_ref.invoice_ids[0]
                            # Update reference
                            invoice.write({'invoice_id_ref': invoice_id_ref.id}) 
                            # Update reference back to the original
                            invoice_id_ref.write({'invoice_id_ref': invoice.id}) 
        return res
    
    @api.model
    def _prepare_refund(self, invoice, date=None, period_id=None, description=None, journal_id=None):
        res = super(account_invoice, self)._prepare_refund(invoice, date=date, period_id=period_id, description=description, journal_id=journal_id)
        res['invoice_id_ref'] = invoice.id
        return res
     
    @api.multi
    @api.returns('self')
    def refund(self, date=None, period_id=None, description=None, journal_id=None):
        new_ids = super(account_invoice, self).refund(date=date, period_id=period_id, description=description, journal_id=journal_id)
        for new_invoice in new_ids:
            if new_invoice.invoice_id_ref:
                new_invoice.invoice_id_ref.write({'invoice_id_ref': new_invoice.id})
        return new_ids        
