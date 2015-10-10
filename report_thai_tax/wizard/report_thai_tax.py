# -*- encoding: utf-8 -*-
from openerp import models, fields, api, _
import time

class report_thai_tax_wizard(models.Model):

    _name = 'report.thai.tax.wizard'

    def onchange_tax_id(self, cr, uid, ids, tax_id, context=None):
        if not tax_id:
            return {'value': {}}
        tax = self.pool.get('account.tax').browse(cr, uid, tax_id, context)
        return {'value': {'base_code_id': tax.base_code_id.id,
                         'tax_code_id': tax.tax_code_id.id,
                         'type_tax_use': tax.type_tax_use, }}
    
    @api.model
    def _get_company(self):
        user_pool = self.pool.get('res.users')
        company_pool = self.pool.get('res.company')
        company_id = self.env.user.company_id
        if not company_id:
            company_id = company_pool.search([], limit=1)
        else:
            company_id = company_id.id
        return company_id or False
    
    @api.model
    def _get_period(self):
        """Return default period value"""
        ctx = dict(self._context or {}, account_period_prefer_normal=True)
        period_ids = self.env['account.period'].with_context(ctx).find()
        return period_ids

    company_id = fields.Many2one('res.company', string='Company', required=True, default=_get_company)
    period_id = fields.Many2one('account.period', string='Period', required=True, default=_get_period)
    tax_id = fields.Many2one('account.tax', string='Tax', domain=[('type_tax_use', 'in', ('sale', 'purchase')), ('is_wht', '=', False), ('is_suspend_tax', '=', False)], required=True)
    base_code_id = fields.Many2one('account.tax.code', string='Base Code', domain=[('id', '=', False)], required=True)
    tax_code_id = fields.Many2one('account.tax.code', string='Tax Code', required=True)
    type_tax_use = fields.Selection(selection=[('sale', 'Sale'), ('purchase', 'Purchase'), ('all', 'All')], string='Tax Application', required=True)

    @api.v7
    def start_report(self, cr, uid, ids, data, context=None):
        for wiz_obj in self.read(cr, uid, ids):
            if 'form' not in data:
                data['form'] = {}
            data['form']['company_id'] = wiz_obj['company_id'][0]
            data['form']['period_id'] = wiz_obj['period_id'][0]
            data['form']['tax_id'] = wiz_obj['tax_id'][0]
            data['form']['base_code_id'] = wiz_obj['base_code_id'][0]
            data['form']['tax_code_id'] = wiz_obj['tax_code_id'][0]
            data['form']['type_tax_use'] = wiz_obj['type_tax_use']
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'report_thai_tax',
                'datas': data,
            }
