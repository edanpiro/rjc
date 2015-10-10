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
import logging
from openerp import models, fields, api, _
from openerp.exceptions import Warning

_logger = logging.getLogger(__name__)

class account_move(models.Model):
    _inherit = 'account.move'
    
    @api.model
    def process_account_post(self, journal_ids=None):
        if journal_ids:
            filters = ['&', ('state', '=', 'draft'), ('journal_id', 'in', journal_ids)]
        else:
            filters = [('state', '=', 'draft')]
        ids_move = self.search(filters)
        try:
            if ids_move:
                ids_move.button_validate()
        except Exception:
            _logger.exception("Failed processing account posting")



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
