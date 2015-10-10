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

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    shipper_id = fields.Many2one('partner.shipper', string='Shipper', domain="[('partner_ids', 'in', partner_id)]")
    
    @api.multi
    def action_invoice_create(self, journal_id=False, group=False, type='out_invoice'):
        res = super(stock_picking, self).action_invoice_create(journal_id=journal_id, group=group, type=type)
        if type == 'out_invoice':
            for picking_id in self:
                inv_obj = self.env['account.invoice']
                for invoice_id in res:
#                     invoice_id = res.get(picking_id)
                    invoice = inv_obj.browse(invoice_id)
                    picking = picking_id
                    invoice.write({'shipper_id': picking.shipper_id.id})
        return res
    
    # After partial delivery, also copy the shipper_id from Old DO to new DO
    #TODO: No need of this module shipper transfer to backorder
#     @api.cr_uid_ids_context
#     def do_transfer(self, cr, uid, picking_ids, context=None):
#         res = super(stock_picking, self).do_partial(cr, uid, picking_ids, context=context)
#         if res:
#             original_picking = res.keys()[0]
#             delivered_picking = res[res.keys()[0]]['delivered_picking']
#             if original_picking <> delivered_picking:
#                 results = original_picking.read(['shipper_id'])
#                 shipper_id = results[0]['shipper_id'] and results[0]['shipper_id'][0] or False
#                 delivered_picking.write({'shipper_id': shipper_id})
#         return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: