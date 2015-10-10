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
import re

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    @api.multi
    def action_invoice_create(self, journal_id=False, group=False, type='out_invoice'):
        res = super(stock_picking, self).action_invoice_create(journal_id, group, type)
        if type == 'out_refund':
            refund_invoice_ids = res
            if not isinstance(refund_invoice_ids, list):
                refund_invoice_ids = [refund_invoice_ids]
            # Test matching xxx-yyy-return, then the yyy will be original doc
            if re.match("^[a-zA-Z0-9._%-+/]+-[a-zA-Z0-9._%-+/]+-return", self.name) != None:
                ref_picking_name = re.search('-(.*?)-return', self.name).group(1)
                ref_picking_ids = self.search([('name', '=', ref_picking_name)])
                if len(ref_picking_ids) > 0:
                    ref_picking = self.browse(ref_picking_ids[0])
                    for ref_invoice in ref_picking.invoice_ids:
                        refund_invoice_ids.write({
                            'origin_invoices_ids': [(4, ref_invoice.id)],
                            # 'refund_invoices_description': ''
                        })                 
        return res
