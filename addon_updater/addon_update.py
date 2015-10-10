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
import os
import zipfile
from os.path import join as opj
from bzrlib.branch import Branch
import bzrlib.directory_service
import filecmp
import shutil
import logging
from openerp import pooler
import subprocess
from openerp.exceptions import Warning

_logger = logging.getLogger(__name__)

class addon_update(models.Model):

    _name = "addon.update"
    _description = 'Addon Update Worksheet'

    name = fields.Char('Name', size=64, required=True, readonly=True, default='/')
    config_id = fields.Many2one('addon.config', 'Addon Project', required=True, readonly=True, states={'draft': [('readonly', False)], 'check': [('readonly', False)]})
    update_lines = fields.One2many('addon.update.line', 'update_id', 'Update Lines', ondelete='cascade', readonly=True, states={'draft': [('readonly', False)], 'check': [('readonly', False)]})
    revision = fields.Integer('Revision', readonly=True)
    check_time = fields.Datetime('Last Check', readonly=True)
    state = fields.Selection(selection=[('draft', 'Draft'),
                               ('check', 'Checked'),
                               ('ready', 'Ready'),
                               ('done', 'Updated'),
                               ('revert', 'Reverted'),
                               ('cancel', 'Cancelled')], string='Status', default='draft', required=True, readonly=True,
            help='* The \'Draft\' status is set when the work sheet in draft status. \
                \n* The \'Checked\' status is set when project folder has been download and check for updated modules. \
                \n* The \'Ready\' status is set when server has been restarted, and module are ready to upgrade. \
                \n* The \'Updated\' status is set when things goes well, all selected module has been updated. \
                \n* The \'Reverted\' status is set when things goes wrong, module will be set back to previous version. \
                \n* The \'Cancelled\' status is set when a user cancel the work sheet.')
    note = fields.Text('Notes')

    _order = 'id desc'
    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get('addon.update.sheet') or '/'
        config = self.env['addon.config'].browse(vals['config_id'])
        try:
            revisison, rev_id = Branch.open(config.root_path).last_revision_info()
            vals.update({'revision': revisison})
        except Exception, e:
            _logger.exception(str(e))
        return super(addon_update, self).create(vals)
    
    @api.model
    def _add_to_update_list(self, update_id, module_name, result):
        if module_name == 'addon_updater':
            return False
        module_obj = self.env['ir.module.module']
        update_line_obj = self.env['addon.update.line']
        # From mod_name, find the module_id. But if not exist, change type = 'new'
        module = module_obj.search([('name', '=', module_name)], limit=1)
        if not module:
            line_dict = {
                'name': module_name,
                'update_id': update_id,
                'select': False,
                'module_id': False,
                'type': 'new',
                'state': 'new'
            }
        else:
            line_dict = {
                'update_id': update_id,
                'name': module.name,
                'select': False,
                'module_id': module.id,
                'type': result['type'],
                'changed_files': ', '.join(str(x) for x in result['changed_files']),
                'added_files': ', '.join(str(x) for x in result['added_files']),
                'removed_files': ', '.join(str(x) for x in result['removed_files']),
                'state': module.state,
            }
        return update_line_obj.create(line_dict)
    
    @api.model
    def _update_from_bzr(self, addon_id):
        addon_obj = self.env['addon.config']
        addon_config = addon_obj.browse(addon_id)
        if addon_config:
            if addon_config.bzr_source:
                if not os.path.exists(addon_config.root_path):
                    # this helps us determine the full address of the remote branch
                    branchname = bzrlib.directory_service.directories.dereference(addon_config.bzr_source)
                    # let's now connect to the remote branch
                    remote_branch = Branch.open(branchname)
                    # download the branch
                    remote_branch.bzrdir.sprout(addon_config.root_path).open_branch()
                else:
                    b1 = Branch.open(addon_config.root_path)
                    b2 = Branch.open(addon_config.bzr_source)
                    b1.pull(b2)
                    subprocess.call(["bzr", "up", addon_config.root_path])
                    #b1.update()
        b1 = Branch.open(addon_config.root_path)
        revno, rev_id = b1.last_revision_info()
        return revno
    
    @api.model
    def _get_modules(self, path):
        """Returns the list of module names
        """
        def listdir(dir):
            def clean(name):
                name = os.path.basename(name)
                if name[-4:] == '.zip':
                    name = name[:-4]
                return name

            def is_really_module(name):
                manifest_name = opj(dir, name, '__openerp__.py')
                zipfile_name = opj(dir, name)
                return os.path.isfile(manifest_name) or zipfile.is_zipfile(zipfile_name)
            return map(clean, filter(is_really_module, os.listdir(dir)))

        plist = []
        plist.extend(listdir(path))
        return list(set(plist))
    
    @api.model
    def _compute_diff_files(self, dcmp, changed_files=[], added_files=[], removed_files=[], exclude=['pyc', 'jasper', '~1~', '~2~']):
        changed_files += filter(lambda a: a.split('.')[-1] not in exclude, dcmp.diff_files)
        added_files += filter(lambda a: a.split('.')[-1] not in exclude, dcmp.left_only)
        removed_files += filter(lambda a: a.split('.')[-1] not in exclude, dcmp.right_only)
        for sub_dcmp in dcmp.subdirs.values():
            self._compute_diff_files(sub_dcmp, changed_files, added_files,
                                   removed_files, exclude=exclude)
    @api.model
    def _compare_version(self, addon_config, module_name):
        result = {'type': False,
                  'changed_files': [],
                  'added_files': [],
                  'removed_files': []
                  }
        sourcedir = os.path.join(addon_config.root_path, module_name)
        destdir = os.path.join(addon_config.production_path, module_name)
        if not os.path.isdir(sourcedir):
            return result
        if not os.path.isdir(destdir):
            result.update({'type': 'new'})
            return result
        # Compare folder
        changed_files, added_files, removed_files = [], [], []
        self._compute_diff_files(filecmp.dircmp(sourcedir, destdir), changed_files, added_files, removed_files)
        if changed_files + added_files + removed_files:
            result.update({'type': 'update',
                          'changed_files': changed_files,
                          'added_files': added_files,
                          'removed_files': removed_files})
        return result
    
    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
    
    @api.multi
    def action_check(self):
        # Delete lines first
        update_line_obj = self.env['addon.update.line']
        lines = update_line_obj.search([('update_id', 'in', self.ids)])
        lines.unlink()
        # Update local branch
        for update in self:
            config = update.config_id
            # Delete backup directory, it will be created in action_sent
            if os.path.isdir(config.backup_path):
                shutil.rmtree(config.backup_path)
            try:
                revision = self._update_from_bzr(config.id)
            except Exception, e:
                raise Warning(_('Error Bazaar!'), str(e))
            # Compare each addon, if mismatch, add to list
            mod_names = self._get_modules(config.root_path)
            for mod_name in mod_names:
                result = self._compare_version(config, mod_name)  # Return type, list of diff files
                if result['type'] in ['new', 'update']:
                    self._add_to_update_list(update.id, mod_name, result)

            update.write({'state': 'check',
                          'revision': revision,
                          'check_time': time.strftime("%Y-%m-%d %H:%M:%S")})
        return True
    
    @api.multi
    def action_sent(self):
        for update in self:
            config = update.config_id
            # Create backup directory if not exists
            if not os.path.isdir(config.backup_path):
                os.mkdir(config.backup_path)
            # Get upgrade list and move folders
            install_list = []
            upgrade_list = []
            for update_line in update.update_lines:
                if update_line.select == True:
                    if update_line.type == 'new':
                        install_list.append(update_line.name)
                    if update_line.type == 'update':
                        upgrade_list.append(update_line.name)
                    sourcedir = os.path.join(config.root_path, update_line.name)
                    backupdir = os.path.join(config.backup_path, update_line.name)
                    destdir = os.path.join(config.production_path, update_line.name)
                    # Backup first
                    if os.path.isdir(destdir):
                        shutil.move(destdir, backupdir)
                    # Copy from local to production
                    shutil.copytree(sourcedir, destdir)

            if not install_list + upgrade_list:
                raise Warning(_('Warning!'), _('You have not select any addons to install/upgrade!'))

            update.write({'state': 'ready'})

            # Update module list
            module_obj = self.env['ir.module.module']
            module_obj.update_list()

            # Update ir_module_module state
            to_installs = module_obj.search([('name', 'in', install_list)])
            to_upgrades = module_obj.search([('name', 'in', upgrade_list)])
            to_installs.write({'state': 'to install'})
            to_upgrades.write({'state': 'to upgrade'})

        return True
    
    @api.multi
    def upgrade_module(self):
        ir_module = self.env['ir.module.module']

        # install/upgrade: double-check preconditions
        modules = ir_module.search([('state', 'in', ['to upgrade', 'to install'])])
        if modules:
            cr.execute("""SELECT d.name FROM ir_module_module m
                                        JOIN ir_module_module_dependency d ON (m.id = d.module_id)
                                        LEFT JOIN ir_module_module m2 ON (d.name = m2.name)
                          WHERE m.id in %s and (m2.state IS NULL or m2.state IN %s)""",
                      (tuple(modules.ids), ('uninstalled',)))
            unmet_packages = [x[0] for x in cr.fetchall()]
            if unmet_packages:
                raise Warning(_('Unmet Dependency!'),
                                     _('Following modules are not installed or unknown: %s') % ('\n\n' + '\n'.join(unmet_packages)))

            modules.download()
            cr.commit()  # save before re-creating cursor below

        # Change state, if not specified, set to done.
        self.write({'state': self.env.context.get('to_state', False) or 'done'})

        pooler.restart_pool(cr.dbname, update_module=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'wait': True},
        }
    
    @api.multi
    def action_revert(self):
        for update in self:
            config = update.config_id
            # If not backup path, raise error message
            if not os.path.isdir(config.backup_path):
                raise Warning(_('No backup!'),
                                     _('Backup folder %s does not exists. Revert fail!') % (config.backup_path,))
            # Get upgrade list and move folders
            install_list = []
            upgrade_list = []
            for update_line in update.update_lines:
                if update_line.select == True:
                    if update_line.type == 'new':
                        install_list.append(update_line.name)
                    if update_line.type == 'update':
                        upgrade_list.append(update_line.name)
                    backupdir = os.path.join(config.backup_path, update_line.name)
                    destdir = os.path.join(config.production_path, update_line.name)
                    # Copy from back from backup to production
                    if os.path.isdir(destdir):
                        shutil.rmtree(destdir)
                    if os.path.isdir(backupdir):
                       shutil.copytree(backupdir, destdir)
            update.write({'state': 'revert'})

            # Update ir_module_module state
            module_obj = self.env['ir.module.module']
            to_installs = module_obj.search([('name', 'in', install_list)])
            to_upgrades = module_obj.search([('name', 'in', upgrade_list)])
            to_installs.write({'state': 'uninstalled'})  # to remove
            to_installs.unlink()  # remove it.
            to_upgrades.write({'state': 'to upgrade'})
        
        ctx = self.env.context.copy()

        ctx.update({'to_state': 'revert'})
        self.with_context(ctx).upgrade_module()
        return True

class addon_update_line(models.Model):

    _name = "addon.update.line"
    _description = 'Addon Update Lines'

    update_id = fields.Many2one('addon.update', 'Addon Update', required=True)
    select = fields.Boolean('Select', required=False, default=False)
    module_id = fields.Many2one('ir.module.module', 'Module', readonly=True, required=False)
    name = fields.Char('Technical Name', size=64, readonly=True, required=False)
    type = fields.Selection([
        ('new', 'New'),  # New state for package not available on production yet.
        ('update', 'Updated'),
    ], string='Type', readonly=True)
    changed_files = fields.Text('Changed Files', readonly=True)
    added_files = fields.Text('Added Files', readonly=True)
    removed_files = fields.Text('Removed Files', readonly=True)
    state = fields.Selection([
        ('new', 'New'),  # New state for package not available on production yet.
        ('uninstallable', 'Not Installable'),
        ('uninstalled', 'Not Installed'),
        ('installed', 'Installed'),
        ('to upgrade', 'To be upgraded'),
        ('to remove', 'To be removed'),
        ('to install', 'To be installed')
    ], string='Status', readonly=True, index=True)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
