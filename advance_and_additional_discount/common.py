
from openerp import api, fields, models, _
from openerp.exceptions import Warning

class AdditionalDiscountable(object):
    _line_column = 'order_line'
    _tax_column = 'tax_id'
    
    @api.model
    def record_currency(self, record):
        """Return currency browse self from a browse self.

        Default implementation is for sale/purchase order.
        """
        return self.pricelist_id.currency_id
    
    @api.one
    def _amount_sale_generic(self, cls):
        """Generic overload of the base method to add discount infos

        This is a generic version that needs to be passed the caller class (for
        super).
        For now it can be applied to sale.order, purchase.order and
        account.invoice, using the methods and attrs of AdditionalDiscountable
        """
        super(cls, self)._amount_all_wrapper()

        # Taxes are applied line by line, we cannot apply a
        # discount on taxes that are not proportional
        if not all(t.type == 'percent'
                   for line in getattr(self, self._line_column)
                   for t in getattr(line, self._tax_column)):
            raise Warning(_('Discount error'),
                                 _('Unable (for now) to compute a global '
                                   'discount with non percent-type taxes'))
#             o_res = res[self.id]
        cur = self.record_currency(self)
        def cur_round(value):
            """Round value according to currency."""
            return cur.round(value)

        # add discount
        amount_untaxed = sum(line.price_subtotal for line in getattr(self, self._line_column))
        add_disc = self.add_disc
        add_disc_amt = cur_round(amount_untaxed * add_disc / 100)
        self.add_disc_amt = add_disc_amt
        self.amount_net = self.amount_untaxed - add_disc_amt
        self.amount_total = self.amount_net + self.amount_tax
    
    @api.one
    def _amount_all_generic(self, cls):
        """Generic overload of the base method to add discount infos

        This is a generic version that needs to be passed the caller class (for
        super).
        For now it can be applied to sale.order, purchase.order and
        account.invoice, using the methods and attrs of AdditionalDiscountable
        """
        super(cls, self)._amount_all()

        # Taxes are applied line by line, we cannot apply a
        # discount on taxes that are not proportional
        if not all(t.type == 'percent'
                   for line in getattr(self, self._line_column)
                   for t in getattr(line, self._tax_column)):
            raise Warning(_('Discount error'),
                                 _('Unable (for now) to compute a global '
                                   'discount with non percent-type taxes'))
#             o_res = res[self.id]
        cur = self.record_currency(self)
        def cur_round(value):
            """Round value according to currency."""
            return cur.round(value)

        # add discount
        amount_untaxed = sum(line.price_subtotal
                             for line in getattr(self, self._line_column))
        add_disc = self.add_disc
        add_disc_amt = cur_round(amount_untaxed * add_disc / 100)
        self.add_disc_amt = add_disc_amt
        self.amount_net = self.amount_untaxed - add_disc_amt
        self.amount_total = self.amount_net + self.amount_tax

    # Kittiu: Same as the above but only use for invoice to correct the Tax amount
    # Note that we do not correct the Tax amount, as it is already in tax table.
    @api.one
    def _amount_invoice_generic(self, cls):
        """Generic overload of the base method to add discount infos

        This is a generic version that needs to be passed the caller class (for
        super).
        For now it can be applied to sale.order, purchase.order and
        account.invoice, using the methods and attrs of AdditionalDiscountable
        """
        super(cls, self)._amount_all()
        
        # Taxes are applied line by line, we cannot apply a
        # discount on taxes that are not proportional
        if not all(t.type == 'percent'
                   for line in getattr(self, self._line_column)
                   for t in getattr(line, self._tax_column)):
            raise Warning(_('Discount error'),
                                 _('Unable (for now) to compute a global '
                                   'discount with non percent-type taxes'))
            
        cur = self.record_currency(self)
        
        if isinstance(cur, int): #TODO Need to check this method
            cur = self.env['res.currency'].browse(cur)
                    
        def cur_round(value):
            """Round value according to currency."""
            return cur.round(value)

        # add discount
        amount_untaxed = sum(line.price_subtotal
                             for line in getattr(self, self._line_column))
        add_disc = self.add_disc
        add_disc_amt = cur_round(amount_untaxed * add_disc / 100)
        self.add_disc_amt = add_disc_amt
        self.amount_net = self.amount_untaxed - add_disc_amt

        # add advance amount, if is_advance = True and advance_percentage > 0
        self.amount_advance = 0.0
        self.amount_deposit = 0.0
        self.amount_beforetax = self.amount_net

        # Modify BY DRB, get order from stock picking
        order = False
        # order = order or self.picking_ids and (self.picking_ids[0].sale_id or self.picking_ids[0].purchase_id)
        order = order or (self.sale_order_ids and self.sale_order_ids[0]) or (self.purchase_order_ids and self.purchase_order_ids[0])
        if order:
#             if self.sale_order_ids or self.purchase_order_ids:
#                 order = self.sale_order_ids and self.sale_order_ids[0] or self.purchase_order_ids[0]
            if not self.is_advance:
                advance_percentage = order.advance_percentage
                if advance_percentage:
                    self.amount_advance = cur_round(self.amount_net * advance_percentage / 100)
                    self.amount_beforetax = cur_round(self.amount_beforetax) - cur_round(self.amount_advance)
            if not self.is_deposit:
                # Deposit will occur only in the last invoice (invoice that make it 100%)
                # this_invoice_rate = order.amount_net and cur_round(o_res['amount_beforetax']) * 100 / order.amount_net or 0.0
                # amount_deposit = order.invoiced_rate + this_invoice_rate >= 100.0 and order.amount_deposit or False
                amount_deposit = order.invoiced_rate >= 100.0 and order.amount_deposit or False
                if amount_deposit:
                    self.amount_deposit = amount_deposit
                    self.amount_beforetax = self.amount_beforetax - self.amount_deposit

        # add retention amount, if is_retention = True and retention_percentage > 0
        self.amount_beforeretention = self.amount_beforetax + self.amount_tax
        self.amount_retention = 0.0
        if self.sale_order_ids:
            order = self.sale_order_ids and self.sale_order_ids[0]
            if self.is_retention:
                retention_percentage = order.retention_percentage
                if retention_percentage:
                    self.amount_retention = (self.amount_net * retention_percentage / 100)

        self.amount_total = self.amount_beforeretention - self.amount_retention

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: