
from openerp import api, fields, models, _

class ir_values(models.Model):
    _inherit = "ir.values"
    
    # Overriding method
    @api.model
    def get_actions(self, action_slot, model, res_id=False):
        result = super(ir_values, self).get_actions(action_slot, model, res_id)
        
        if result and action_slot == 'client_print_multi':
            tmp_result = []
            for ls in result:
                if ls[2]:
                    ls2 = ls[2]
                    if ls2.get('type', False) == 'ir.actions.report.xml' and ls2.get('invisible', False):
                        if  not eval(ls2.get('invisible')):
                            tmp_result.append(ls)
#                         mod_obj = self.pool.get(ls2.get('model'))
#                         ids = mod_obj.search(cr, uid,eval('list('+ls2.get('domain')+')'))
#                         if ids:
#                             tmp_result.append(ls)
                    else:
                        tmp_result.append(ls)
                else:
                    tmp_result.append(ls)
                    
            result = tmp_result
        return result
