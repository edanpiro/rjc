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

# This file will contain all create account_move method of every document.

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.multi
    def action_move_create(self):
        ctx = dict(self._context)
        if self.type in ('out_invoice', 'out_refund'):
            ctx.update({'pricelist_type': 'sale'})
        elif self.type in ('in_invoice', 'in_refund'):
            ctx.update({'pricelist_type': 'purchase'})
        self.with_context(ctx)
        return super(account_invoice, self).action_move_create()
 
class account_voucher(models.Model):
    _inherit = 'account.voucher'
    
    @api.multi
    def action_move_line_create(self):
        ctx = dict(self._context)
        if self.type in ('sale', 'receipt'):
            ctx.update({'pricelist_type': 'sale'})
        elif self.type in ('purchase', 'payment'):
            ctx.update({'pricelist_type': 'purchase'})
        self.with_context(ctx)
        return super(account_voucher, self).action_move_line_create()
 
class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    @api.cr_uid_ids_context
    def do_transfer(self, cr, uid, picking_ids, context=None):
        if context is None:
            context = {}
        # pass pricelist_type variable based on pick.type, this will be passed to the currency.compute()
        pick_types = list(set([x.picking_type_id.code for x in self.browse(cr, uid, picking_ids)]))
        if len(pick_types) > 1:
            raise Warning(_('Error'), _('Mixed Picking In/Out not allowed!'))
        ctx = (context.copy() or {})
        if len(pick_types) == 1:
            if pick_types[0] == 'incoming':
                ctx.update({'pricelist_type': 'purchase'})
                cr.pricelist_type = 'sale'  # Actually this is not a proper way of passing value, but no choice.
            elif pick_types[0] == 'outgoing':
                ctx.update({'pricelist_type': 'sale'})
#             self._cr.pricelist_type = 'purchase'
        return super(stock_picking, self).do_transfer(cr, uid, picking_ids, context=ctx)
         
class res_currency(models.Model):
    _inherit = 'res.currency'
    
    @api.v8
    def compute(self, from_amount, to_currency_id, round=True):
        ctx = dict(self._context)
        if hasattr(self._cr, 'pricelist_type') and self._cr.pricelist_type:  # because problem with stock.do_partial(), which not pass context, we pass it this here.
            ctx.update({'pricelist_type': self._cr.pricelist_type})
            self.with_context(ctx)
        return super(res_currency, self).compute(from_amount, to_currency_id, round=round)
    
    @api.v7 
    def compute(self, cr, uid, from_currency_id, to_currency_id, from_amount, round=True, context=None):
        if not context:
            context = {}
        if hasattr(cr, 'pricelist_type') and cr.pricelist_type:  # because problem with stock.do_partial(), which not pass context, we pass it this here.
            context.update({'pricelist_type': cr.pricelist_type})
        return super(res_currency, self).compute(cr, uid, from_currency_id, to_currency_id, from_amount, round=round, context=context)
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: