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
from openerp.exceptions import Warning

class sale_confirm(models.TransientModel):
    """
    This wizard will confirm the all the selected draft quotation
    """
    _name = "sale.confirm"
    _description = "Confirm the selected quotations"
    
    @api.multi
    def sale_confirm(self):
        data_inv = self.env['sale.order'].browse(self._context['active_ids'])
        for record in data_inv:
            if record['state'] not in ('draft'):
                raise Warning(_('Warning!'), _("Selected quotation(s) cannot be confirmed as they are not in 'Draft'."))
#             wf_service.trg_validate(uid, 'sale.order', record['id'], 'order_confirm', cr)
            record.signal_workflow('order_confirm')
            
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: