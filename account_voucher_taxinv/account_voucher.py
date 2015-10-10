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

import openerp.addons.decimal_precision as dp
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_voucher(models.Model):
    
    @api.one
    @api.depends('voucher_taxinv')
    def _is_taxinv(self):
        if len(self.voucher_taxinv):
            self.is_taxinv = True

    _inherit = 'account.voucher'

    is_taxinv = fields.Boolean(compute='_is_taxinv', string='Has Suspended Tax Invoice')
    voucher_taxinv = fields.One2many('account.voucher.taxinv', 'voucher_id', string='Voucher VAT Info')
    is_taxinv_publish = fields.Boolean(string='Tax Invoice Published', help="If published, this information will be shown in Tax Report for the specified period")
    taxinv_period_id = fields.Many2one('account.period', string='Tax Invoice Period', readonly=True)
    is_basevat_invalid = fields.Boolean(string='Base/Vat Invalid', help="Base amount or amount not equal to its accounting entry")

    @api.multi
    def to_publish(self):
        ctx = dict(self._context)
        is_basevat_invalid = False
        for voucher in self:
            # Check for base / tax amount
            if voucher.type == 'payment':
                avtax_obj = self.env['account.voucher.tax']
                ctx.update({'is_taxinv': True})
                base_amount = tax_amount = base_amount2 = tax_amount2 = 0.0
                for tax in avtax_obj.with_context(ctx).compute(voucher.id).values():
                    base_amount += tax['base']
                    tax_amount += tax['amount']
                for taxinv in voucher.voucher_taxinv:
                    base_amount2 += taxinv.base_amount
                    tax_amount2 += taxinv.tax_amount
                if base_amount != base_amount2 or tax_amount != tax_amount2:
                    is_basevat_invalid = True
            # Period Check
            if not voucher.taxinv_period_id:
                raise Warning(_('Warning!'), _('Tax Invoice Period is not specified!'))
        return self.write({'is_taxinv_publish': True, 'is_basevat_invalid': is_basevat_invalid})
    
    @api.multi
    def to_unpublish(self):
        for voucher in self:
            return voucher.write({'is_taxinv_publish': False})
    
    @api.multi
    def button_reset_taxinv(self):
        ctx = dict(self._context)
        avtax_obj = self.env['account.voucher.tax']
        avtin_obj = self.env['account.voucher.taxinv']
        for voucher in self:
            voucher.with_context(ctx)
            if voucher.type == 'payment':
                voucher.write({'taxinv_period_id': voucher.period_id and voucher.period_id.id or False})
                voucher._cr.execute("DELETE FROM account_voucher_taxinv WHERE voucher_id=%s ", (voucher.id,))
                ctx.update({'is_taxinv': True})
                for tax in avtax_obj.with_context(ctx).compute(voucher.id).values():
                    tax.update({'date': voucher.date})
                    avtin_obj.create(tax)
        return True

    @api.multi
    def proforma_voucher(self):
        super(account_voucher, self).proforma_voucher()
        self.button_reset_taxinv()
        return True

#     # For backward compatibility
#     def init(self, cr):
#         # Check where there are any existing records in account_voucher_taxinv
#         cr.execute("select count(*) from account_voucher_taxinv")
#         res = cr.fetchone()
#         if not res[0]:
#             cr.execute("select id from account_voucher where state in ('proforma', 'posted')")
#             voucher_ids = [x['id'] for x in cr.dictfetchall()]
#             self.button_reset_taxinv(cr, 1, voucher_ids)

class account_voucher_taxinv(models.Model):
    _name = 'account.voucher.taxinv'
    _description = 'Supplier Payment Tax Invoice'

    voucher_id = fields.Many2one('account.voucher', string='Ref Voucher')
    #  'invoice_id': fields.many2one('account.invoice', 'Supplier Invoice'),
    account_id = fields.Many2one('account.account', string='Account')
    date = fields.Date(string='Date', help='This date will be used as Tax Invoice Date in VAT Report')
    number = fields.Char(string='Number', help='Number Tax Invoice')
    #  'partner_id': fields.many2one('res.partner', 'Supplier', size=128, readonly=True, help='Name of Organization to pay Tax'),
    base_amount = fields.Float(string='Base', digits_compute=dp.get_precision('Account'))
    tax_id = fields.Many2one('account.tax', string='Tax', domain=[('is_suspend_tax', '=', True), ('type_tax_use', '=', 'purchase')], required=True, readonly=False)
    tax_amount = fields.Float(string='VAT', digits_compute=dp.get_precision('Account'))

#     def compute(self, cr, uid, voucher_id, context=None):
#         voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=context)
#         advance_and_discount = {}
#         for voucher_line in voucher.line_ids:
#             invoice = voucher_line.move_line_id.invoice
#             if invoice:
#                 adv_disc_param = self.pool.get('account.voucher.line').get_adv_disc_param(cr, uid, invoice)
#                 # Add to dict
#                 advance_and_discount.update({invoice.id: adv_disc_param})
#         tax_grouped = self.pool.get('account.voucher.tax').compute_ex(cr, uid, voucher_id, advance_and_discount, context=context)
#         return tax_grouped

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: