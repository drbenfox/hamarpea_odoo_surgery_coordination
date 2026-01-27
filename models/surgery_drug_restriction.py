from odoo import models, fields


class SurgeryDrugRestriction(models.Model):
    _name = 'surgery.drug.restriction'
    _description = 'Drug Restriction for Surgery'

    name = fields.Char(string='Drug Name', required=True)

    category = fields.Selection([
        ('anticoagulant', 'Anticoagulant'),
        ('diabetes', 'Diabetes Medication'),
        ('other', 'Other')
    ], string='Category')

    automation_data = fields.Json(
        string='Automation Instructions',
        help='JSON: {"days_before": 7, "message": "Stop taking [drug] today"}'
    )

    active = fields.Boolean(default=True)
