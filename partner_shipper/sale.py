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

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    shipper_id = fields.Many2one('partner.shipper', string='Shipper', domain="[('partner_ids', 'in', partner_id)]")
    
    @api.v7
    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        res = super(sale_order, self).onchange_partner_id(cr, uid, ids, part, context=context)
        val = res.get('value')
        # get the first shipper and assign it.
        shipper_ids = self.pool.get('partner.shipper').search(cr, uid, [('partner_ids', 'in', part)])
        val['shipper_id'] = shipper_ids and shipper_ids[0] or False
        return {'value': val}
    
    @api.multi
    def action_invoice_create(self, grouped=False, states=None, date_invoice=False):
        res = super(sale_order, self).action_invoice_create(grouped=grouped, states=states, date_invoice=date_invoice)
        inv_obj = self.env['account.invoice']
        inv = inv_obj.browse(res)
        inv.write({'shipper_id': self.shipper_id.id})
        return res
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: