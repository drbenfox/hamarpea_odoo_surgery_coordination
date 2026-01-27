from odoo import models, fields


class SurgeryStage(models.Model):
    _name = 'surgery.stage'
    _description = 'Surgery Case Stages'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    fold = fields.Boolean(string='Folded in Kanban')
    description = fields.Text(string='Description')
