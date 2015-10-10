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
from openerp.exceptions import except_orm, Warning

class account_invoice(models.Model):
    _inherit = "account.invoice"

    # testing: completely overwrite of account_invoice_merge.merge_invoice()
    @api.multi
    def merge_invoice(self, invoices):
        """ Merge draft invoices. Work only with same partner.
            You can merge invoices and refund invoices with echa other.
            Moves all lines on the first invoice.
        """

        if len(invoices) <= 1:
            return False
        parent = self.env['account.invoice'].browse(self._context['active_id'])
        for inv in invoices :
            if parent.partner_id != inv.partner_id :
                raise Warning(_("Partners don't match!"), _("Can not merge invoice(s) on different partners or states !."))

            if inv.state != 'draft' :
                raise Warning(_("Invalid action !"), _("You can merge only invoices in draft state."))

        # Merge invoices that are in draft state
        inv_line_obj = self.env['account.invoice.line']
        name = parent.name
        comment = parent.comment or ''
        origin = parent.origin
        for inv in invoices:
            if inv.id == parent.id:
                continue

            # check if a line with the same product already exist. if so add quantity. else hang up invoice line to first invoice head.
            if inv.name:
                name += ', %s' % inv.name
            if inv.comment:
                comment += ', %s' % inv.comment
            if inv.origin:
                origin += ', %s' % inv.origin
            line_ids = inv_line_obj.search([('invoice_id', '=', inv.id)])
            for inv_lin in line_ids:
                mrg_pdt_ids = inv_line_obj.search([('invoice_id', '=', parent.id), ('product_id', '=', inv_lin.product_id.id),
                                                            ('uos_id', '=', inv_lin.uos_id.id), ('price_unit', '=', inv_lin.price_unit),  # testing: extra condition, unit price must also be the same.
                                                            ('special_info', '=', False), ('prodlot_id', '=', False)])  # testing: extra conditions
                if len(mrg_pdt_ids) == 1 and inv.type == parent.type:  # product found --> add quantity
                    mrg_pdt_ids.write({'quantity': inv_line_obj._can_merge_quantity(mrg_pdt_ids[0].id, inv_lin.id)})
                    inv_lin.unlink()
                elif inv.type == parent.type:
                    inv_lin.write({'invoice_id': parent.id})
                else:
                    inv_lin.write({'invoice_id': parent.id, 'quantity':-inv_lin.quantity})

            parent.write({'origin':origin, 'name':name, 'comment':comment})
            self.env.cr.execute('update sale_order_invoice_rel set invoice_id = %s where invoice_id = %s', (parent.id, inv.id))
            self.env.cr.execute('update picking_invoice_rel set invoice_id = %s where invoice_id = %s', (parent.id, inv.id))
            inv.unlink()

        parent.button_reset_taxes()
        return parent.id

class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.multi    
    def _can_merge_quantity(self, id1, id2):
        qty = False
        invl1 = self.browse(id1)
        invl2 = self.browse(id2)

        if invl1.product_id.id == invl2.product_id.id \
            and invl1.price_unit == invl2.price_unit \
                and invl1.uos_id.id == invl2.uos_id.id \
                and invl1.account_id.id == invl2.account_id.id \
                and invl1.discount == invl2.discount:
            qty = invl1.quantity + invl2.quantity
        return qty

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
