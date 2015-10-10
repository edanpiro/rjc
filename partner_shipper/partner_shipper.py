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

class partner_shipper(models.Model):
    
    _routes = [
        ('north', 'ภาคเหนือ'),
        ('northeast', 'ภาคอีสาน'),
        ('central', 'ภาคกลาง'),
        ('south', 'ภาคใต้'),
        ('other', 'อื่นๆ'),
        ]    
    
    _description = 'Shippers'
    _name = 'partner.shipper'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    route = fields.Selection(_routes, string='Route', required=True)
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    zip = fields.Char(string='Zip', change_default=True)
    city = fields.Char(string='City')
    country = fields.Many2one('res.country', string='Country')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    fax = fields.Char(string='Fax')
    dest_contact = fields.Text(string='Destination Contacts')
    area_covered = fields.Text(string='Convered Area')  
    active = fields.Boolean(string='Active', default=True)
    note = fields.Text(string='Notes')
    partner_ids = fields.Many2many('res.partner', string='Partners')
    
    @api.model
    def _display_address(self, address):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''

        # get the information that will be injected into the display format
        # get the address format
        address_format = "%(street)s\n%(street2)s\n%(city)s %(zip)s\nPhone: %(phone)s\n%(country_name)s"
        args = {
            'country_code': address.country and address.country.code or '',
            'country_name': address.country and address.country.name or '',
        }
        address_field = ['street', 'street2', 'zip', 'city', 'phone']
        for field in address_field :
            args[field] = getattr(address, field) or ''

        return address_format % args
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: