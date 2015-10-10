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

import time
from openerp import models, fields, api, _
import subprocess
import os
import tempfile
from openerp.exceptions import except_orm, RedirectWarning, Warning

class crontab_config(models.Model):
    _loging = os.path.realpath(tempfile.tempdir) + "/crontab_oe.log"
    _root = os.path.realpath(tempfile.tempdir)
        
    _name = 'crontab.config'
    
    name = fields.Char(string='Crontab Name', required=True,)
    note = fields.Text(string='Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Confirmed'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True,
         select=True, default='draft')
    minute = fields.Char(string='Minute', required=True, default='*')
    hour = fields.Char(string='Hour', required=True, default='*')
    day = fields.Char(string='Day of Month', required=True, default='*')
    month = fields.Char(string='Month', required=True, default='*')
    week = fields.Char(string='Day of Week', required=True, default='*')
    command = fields.Char(string='Command', required=True)
    working_path = fields.Char(string='Execute Directory', default=os.path.realpath(tempfile.tempdir))
    active = fields.Boolean(string='Active', default=True)
    last_exec = fields.Datetime(string='Last Manually Execute', readonly=True)
    attfile = fields.Binary(string='Attach File')
    system_flag = fields.Boolean(string='System', readoly=True, default=False) 
    
    @api.multi        
    def get_command(self):
        commands = dict.fromkeys(self.ids, {})
        cron_recs = self.read(['id', 'name', 'command', 'working_path', 'active', 'minute', 'hour', 'day', 'month', 'week', 'state'])
        for cron_rec in cron_recs:
            commands[cron_rec['id']].update({'command':"echo '#Start:OE-->" + (cron_rec.get('name', False) or "") + "';" + 
                                            (cron_rec.get('command', False) or ""),
                                            'name':(cron_rec.get('name', False) or ""),
                                            'active':(cron_rec.get('active', False)) and (cron_rec.get('state', False) == 'done'),
                                            'schedule':(cron_rec.get('minute', False) or "") + " " + (cron_rec.get('hour', False) or "") + " " + 
                                                        (cron_rec.get('day', False) or "") + " " + (cron_rec.get('month', False) or "") + " " + 
                                                        (cron_rec.get('week', False) or "") ,
                                            'working_path':cron_rec.get('working_path', False)
                                    })  
        return commands
    
    @api.multi
    def write(self, vals):           
        res = super(crontab_config, self).write(vals)            
        self.generate_crontab()
        return res
    
    @api.model
    def create(self, vals):
        if vals.get('working_path', False) :
            if len(vals.get('working_path', "")) > 0:
                working_path = vals.get('working_path', "")
                working_path_len = len(working_path)
                if not working_path.endswith("/", working_path_len, working_path_len):
                    vals['working_path'] = vals.get('working_path', "") + "/"
        res_id = super(crontab_config, self).create(vals)
        res_id.generate_crontab()
        return res_id 
    
    @api.multi
    def generate_crontab(self):   
        # Get Command from database                        
        commands = self.get_command()
        working_path = commands[self.id].get('working_path', self._root)
        
        # Create temporary. 
        tmpfn1 = os.tempnam(working_path, 'oe1')
        tmpfn2 = os.tempnam(working_path, 'oe2')
        
        # Extract Crontab to temporary file
        # Note,make sure you have permission to access directory and directory exists.
        p = subprocess.call(["crontab -l > " + tmpfn1], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    
        # Search with "#Start:OE-->" + name crontrab  and delete it.
        subprocess.call(["sed '/#Start:OE-->" + (commands[self.id].get('name', False) or "") + "/d' " + tmpfn1 + " > " + tmpfn2], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        
        if  commands[self.id].get('active', False):  # Active and state is done
            # Append new command into temporary file
            fo = open(tmpfn2, "a")
            fo.write(commands[self.id].get('schedule', "") + " " + commands[self.id].get('command', "") + ">>" + working_path + "/crontab_oe.log\n");
            fo.close()
            
        # Generate the Crontab from file.
        p = subprocess.call(["crontab " + tmpfn2], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    
        # Delete temporary file
        p = subprocess.call(["rm " + tmpfn1], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        p = subprocess.call(["rm " + tmpfn2], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
           
        return True
    
    @api.multi
    def action_button_confirm(self):
        self.write({'state':'done'})
        return True
    
    @api.multi
    def action_button_cancel(self):
        self.write({'state':'cancel'})
        return True
    
    @api.multi
    def action_button_draft(self):
        self.write({'state':'draft'})
        return True
    
    @api.multi
    def action_button_execute(self):
        commands = self.get_command()
        p = subprocess.call([commands[self.id].get('command', "") + ">>" + commands[self.id].get('working_path', self._root) + "/crontab_oe.log\n"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        self.write({'last_exec':time.strftime('%Y-%m-%d %H:%M:%S')})
        return True
    
    @api.multi
    def setup_dbbackup(self):
        _curr_path = os.path.dirname(__file__)
        # id = obj_data.get_object_reference(cr, uid, 'crontab_config','backup_database')[1]
        command = "'%s/db_backup.py' -u openerp -d %s -p '%s'" % (_curr_path, self._cr.dbname, self._root)
        values = {'command':command}
        
        self.write(values)
    
    @api.multi
    def setup_dbrestore(self):
        _curr_path = os.path.dirname(__file__)
        strid = "%s" % ','.join(str(x) for x in self.ids)
        # id = obj_data.get_object_reference(cr, uid, 'crontab_config','backup_database')[1]
        command = "'%s/db_restore.py' -u openerp -d %s -p '%s' -i %s -c 1 " % (_curr_path, self._cr.dbname + "_TEST", self._root, strid)
        values = {'command':command}
        
        self.write(values)
    
    @api.multi
    def unlink(self):
        stat = self.read(['system_flag'])
        for t in stat:
            if t['system_flag']:
                raise Warning(_('Warning!'), _("This is system command, it can't delete."))          
            else:
                # Delete crontab
                self.write({'state':'cancel'})
                # Delete 
                super(crontab_config, self).unlink()
        return True
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: