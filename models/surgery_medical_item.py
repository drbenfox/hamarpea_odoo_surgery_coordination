from odoo import models, fields, api


class SurgeryMedicalItem(models.Model):
    _name = 'surgery.medical.item'
    _description = 'Medical Checklist Item'
    _inherit = ['mail.thread']

    surgery_case_id = fields.Many2one(
        'surgery.case',
        string='Surgery Case',
        required=True,
        ondelete='cascade'
    )

    test_type = fields.Selection([
        ('blood_count', 'Blood Count'),
        ('chemistry', 'Chemistry Panel'),
        ('clotting', 'Clotting Studies'),
        ('vitals', 'Weight/Height/BMI'),
        ('ecg', 'ECG'),
        ('chest_xray', 'Chest X-Ray'),
        ('medical_summary', 'Medical Summary'),
        ('gp_consent', 'GP Consent')
    ], required=True, string='Test Type')

    status = fields.Selection([
        ('awaited', 'Awaited'),
        ('received_normal', 'Received - Normal'),
        ('received_abnormal', 'Received - Abnormal'),
        ('not_applicable', 'Not Applicable')
    ], default='awaited', required=True, tracking=True, string='Status')

    is_required = fields.Boolean(
        compute='_compute_is_required',
        store=True,
        string='Required for this patient'
    )

    notes = fields.Text(string='Comments')

    reviewed_by = fields.Many2one('res.users', string='Reviewed By', readonly=True)
    reviewed_date = fields.Datetime(string='Reviewed Date', readonly=True)

    @api.depends('test_type', 'surgery_case_id.patient_age')
    def _compute_is_required(self):
        for item in self:
            age = item.surgery_case_id.patient_age
            # ECG required if 40+ years
            if item.test_type == 'ecg':
                item.is_required = (age >= 40)
            # Chest X-ray required if 60+ years
            elif item.test_type == 'chest_xray':
                item.is_required = (age >= 60)
            else:
                item.is_required = True

    def write(self, vals):
        """Track who reviewed the item when status changes"""
        if 'status' in vals and vals['status'] != 'awaited':
            vals['reviewed_by'] = self.env.user.id
            vals['reviewed_date'] = fields.Datetime.now()
        return super().write(vals)
