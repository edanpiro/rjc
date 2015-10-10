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

    write_date = fields.Datetime(string='Date Modified', readonly=True)
    write_uid = fields.Many2one('res.users', string='Last Modification User', readonly=True)
    create_date = fields.Datetime(string='Date Created', readonly=True)
    create_uid = fields.Many2one('res.users', string='Creator', readonly=True)    
    
    @api.multi    
    def send_mail_confirm_order_to_sale(self):
        # Send email with template
#         template = self.env['ir.model.data'].get_object('ext_sale_mail', 'confirm_order_to_sale')
        template = self.env.ref('ext_sale_mail.confirm_order_to_sale')
        for order in self:
            if order.user_id and order.user_id.email:
                template.send_mail(order.id, False)
        return True
    
    @api.multi
    def action_button_confirm(self):
        super(sale_order, self).action_button_confirm()
        # Also send email to sales person
        self.send_mail_confirm_order_to_sale()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: