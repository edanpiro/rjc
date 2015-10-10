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
import logging

class sale_order(models.Model):
    _inherit = 'sale.order'
    _logger = logging.getLogger(__name__)
    
    @api.multi
    def action_invoice_create(self, grouped=False, states=['confirmed', 'done', 'exception'], date_invoice=False):
        res = super(sale_order, self).action_invoice_create(grouped, states, date_invoice)
        if not res:
            return res
        self._logger.debug('SO inv create ids,res:%s %s', self.ids, res)

        invoice_ids = res
        if not isinstance(invoice_ids, list):
            invoice_ids = [invoice_ids]
        picking_ids = [picking for picking in self.picking_ids]
        self._logger.debug('PO inv create picking_ids:%s', picking_ids)
        for picking in picking_ids:
            picking.write({'invoice_ids' : [(6, 0, invoice_ids)]}) 
        return res
