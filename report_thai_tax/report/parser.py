# -*- encoding: utf-8 -*-
##############################################################################
#
#
##############################################################################
from openerp.addons.jasper_reports import jasper_report
from openerp.osv import fields, osv
from openerp import pooler
import datetime

def report_thai_tax_parser( cr, uid, ids, data, context ):
    return {
        'parameters': {	
            'company_id': data['form']['company_id'],
            'period_id': data['form']['period_id'],
            'tax_id': data['form']['tax_id'],
            'base_code_id': data['form']['base_code_id'],
            'tax_code_id': data['form']['tax_code_id'],
            'type_tax_use': data['form']['type_tax_use'],
        },
   }

jasper_report.report_jasper(
    'report.report_thai_tax',
    'account.move',
    parser=report_thai_tax_parser
)
