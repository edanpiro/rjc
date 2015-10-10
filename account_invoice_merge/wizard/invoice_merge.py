# -*- coding: utf-8 -*-

#################################################################################
#    Autor: Mikel Martin (mikel@zhenit.com)
#    Copyright (C) 2012 ZhenIT Software (<http://ZhenIT.com>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, fields, models, _
from openerp.exceptions import except_orm, RedirectWarning, Warning
from lxml import etree

class invoice_merge(models.TransientModel):
    """
    Merge invoices
    """
    _name = 'invoice.merge'
    _description = 'Use this wizard to merge draft invoices from the same partner'

    invoices = fields.Many2many('account.invoice', 'account_invoice_merge_rel', 'merge_id', 'invoice_id', string='Invoices')
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(invoice_merge, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=False)
        if self._context is not None and self._context.get('active_id', False):  # testing
            inv_obj = self.env['account.invoice']
            parent = inv_obj.browse(self._context['active_id'])
    
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='invoices']")
            for node in nodes:
                node.set('domain', '["&",("partner_id", "=", ' + str(parent.partner_id.id) + '),("state", "=","draft")]')
            res['arch'] = etree.tostring(doc)
            self.with_context(partner=parent.partner_id.id)
        return res
    
    @api.model
    def default_get(self, fields):
        res = super(invoice_merge, self).default_get(fields)
        if self._context and 'active_ids' in self._context and self._context['active_ids']:
            res.update({'invoices':  self._context['active_ids']})
        return res
    
    @api.multi
    def merge_invoices(self):
        self.invoices.merge_invoice(self.invoices)
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: