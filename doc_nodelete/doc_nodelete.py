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
from openerp.exceptions import except_orm, RedirectWarning, Warning

NO_DELETION_MSG = _('Can not delete document with assigned number %s!')

# Following documents included
# * sale.order (name)
# * purchase.order (name)
# * account.invoice (number)
# * account.voucher (number)
# * account.billing (number)
# * stock.picking (name)
# * stock.picking.out (name)
# * stock.picking.in (name)
# * payment.register (number)

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.multi
    def unlink(self):
        for doc in self:
            if doc.name:
                raise Warning(_('Error!'), NO_DELETION_MSG % (doc.name,))
        return super(sale_order, self).unlink()
      
class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    @api.multi
    def unlink(self):
        for doc in self:
            if doc.name:
                raise Warning(_('Error!'), NO_DELETION_MSG % (doc.name,))
        return super(purchase_order, self).unlink()
      
class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.multi
    def unlink(self):
        for doc in self:
            if doc.number:
                raise Warning(_('Error!'), NO_DELETION_MSG % (doc.number,))
        return super(account_invoice, self).unlink()
      
class account_voucher(models.Model):
    _inherit = 'account.voucher'
    
    @api.multi
    def unlink(self):
        for doc in self:
            if doc.number:
                raise Warning(_('Error!'), NO_DELETION_MSG % (doc.number,))
        return super(account_voucher, self).unlink()
      
class account_billing(models.Model):
    _inherit = 'account.billing'
    
    @api.multi
    def unlink(self):
        for doc in self:
            if doc.number:
                raise Warning(_('Error!'), NO_DELETION_MSG % (doc.number,))
        return super(account_billing, self).unlink()
      
class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    @api.multi
    def unlink(self):
        for doc in self:
            if doc.name:
                raise Warning(_('Error!'), NO_DELETION_MSG % (doc.name,))
        return super(stock_picking, self).unlink()

class payment_register(models.Model):
    _inherit = 'payment.register'
    
    @api.multi
    def unlink(self):
        for doc in self:
            if doc.number:
                raise Warning(_('Error!'), NO_DELETION_MSG % (doc.number,))
        return super(payment_register, self).unlink()
      
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: