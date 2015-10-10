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

from openerp import fields, models, api

class ir_sequence(models.Model):
    
    _inherit = 'ir.sequence'
    
    @api.cr_uid_ids_context
    def _next(self, cr, uid, seq_ids, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        # If no fiscalyear_id passed in, get a default one from today
        if not context.get('fiscalyear_id', False):
            current_year = self.pool['account.fiscalyear'].find(cr, uid)
            ctx.update({'fiscalyear_id': current_year})
        return super(ir_sequence, self)._next(cr, uid, seq_ids, ctx)  

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
