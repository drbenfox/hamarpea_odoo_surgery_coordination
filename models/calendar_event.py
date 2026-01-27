from odoo import models, fields


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    surgery_case_id = fields.Many2one(
        'surgery.case',
        string='Surgery Case'
    )
