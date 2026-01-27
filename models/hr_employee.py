from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Clinical Privilege - Kupot Holim
    kupot_holim_ids = fields.Many2many(
        'res.partner',
        'employee_kupot_holim_rel',
        'employee_id',
        'kupat_holim_id',
        string='Kupot Holim',
        domain=[('account_type', '=', 'kupat_holim')],
        help='Kupot Holim this surgeon can bill directly'
    )

    # Clinical Privilege - Private Insurance
    private_insurance_ids = fields.Many2many(
        'res.partner',
        'employee_private_insurance_rel',
        'employee_id',
        'insurance_id',
        string='Private Insurance',
        domain=[('account_type', '=', 'private_insurance')],
        help='Private insurance companies this surgeon can bill directly'
    )

    # Clinical Privilege - Authorized Procedures
    authorized_procedure_ids = fields.Many2many(
        'product.product',
        'employee_authorized_procedure_rel',
        'employee_id',
        'product_id',
        string='Authorized Procedures',
        domain=[('sale_ok', '=', True)],
        help='Surgical procedures this surgeon is authorized to perform'
    )
