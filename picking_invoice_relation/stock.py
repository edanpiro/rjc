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

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    invoice_ids = fields.Many2many('account.invoice', 'picking_invoice_rel', 'picking_id', 'invoice_id', string='Invoices', copy=False)
#     client_order_ref = fields.Char(related='sale_id.client_order_ref', string="Client Ref", readonly=True) # TODO Currently client_order_ref field does not exits in version 8
    picking_id_ref = fields.Many2one('stock.picking', string='Shipping Ref', readonly=True)
    
    def init(self, cr):
        # This is a helper to guess "old" Relations between pickings and invoices
        cr.execute('select id, origin from account_invoice where length(origin) > 0')
        origins = cr.dictfetchall()
        for origin in origins:
            numbers = origin and origin['origin'] and origin['origin'].replace(' ', '').split(',')
            for number in numbers:
                cr.execute("""
                    insert into picking_invoice_rel(picking_id,invoice_id) select p.id,i.id from stock_picking p, account_invoice i
                    where i.id = %s and p.name = split_part(%s,':',1) and (p.id,i.id) not in (select picking_id,invoice_id from picking_invoice_rel);
                    """, (origin['id'], number,))
                
    @api.multi
    def action_invoice_create(self, journal_id=False, group=False, type='out_invoice'):
        res = super(stock_picking, self).action_invoice_create(journal_id=journal_id, group=group, type=type)
        if not isinstance(res, list):
            res = [res]
        self.write({'invoice_ids' : [(6, 0, res)]}) 
        return res
    
    @api.one
    def copy(self, default=None):
        if default is None:
            default = {}
        if default.get('name') and default.get('name').find('-return'):
            default.update({'picking_id_ref': self.id})
        new_picking = super(stock_picking, self).copy(default)
        # update new id back to original
        
        # If picking also have the invoice ref, make sure the old_picking now point the new picking
        if self.picking_id_ref:
            self.picking_id_ref.write({'picking_id_ref': new_picking.id})
            new_picking.write({'picking_id_ref': self.picking_id_ref.id})
        if new_picking.picking_id_ref:
            self.write({'picking_id_ref': new_picking.id})
        return new_picking    
