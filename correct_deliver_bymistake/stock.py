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
    
    mistake_delivery = fields.Boolean(string='Mistake Delivery', help="This is a mistake delivery that need correction.", default=False, copy=False)
    
    @api.multi
    def action_process_correct_delivery(self):
        """Open the Correct Mistake Delivery Wizard"""
        ctx = dict(self._context)
        ctx = ({
            'active_model': self._name,
            'active_ids': self.ids,
            'active_id': len(self.ids) and self.ids[0] or False
        })
        
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'delivery.correction',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
            'nodestroy': True,
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: