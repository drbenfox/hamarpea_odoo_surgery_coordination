from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError
from datetime import timedelta


class SurgeryCase(models.Model):
    _name = 'surgery.case'
    _description = 'Surgery Case Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'surgery_date desc, id desc'

    # ==================== BASIC INFO ====================
    name = fields.Char(
        string='Case Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: 'New',
        tracking=True
    )

    active = fields.Boolean(default=True)

    # ==================== PATIENT INFO ====================
    partner_id = fields.Many2one(
        'res.partner',
        string='Patient',
        required=True,
        tracking=True,
        domain=[('is_company', '=', False)]
    )

    patient_id_number = fields.Char(
        related='partner_id.vat',
        string='ID Number',
        readonly=True
    )

    patient_age = fields.Integer(
        compute='_compute_patient_age',
        store=True,
        string='Age'
    )

    patient_phone = fields.Char(
        related='partner_id.phone',
        string='Patient Phone',
        readonly=True
    )

    patient_email = fields.Char(
        related='partner_id.email',
        string='Patient Email',
        readonly=True
    )

    # Health Insurance - Combined display (like medical visit)
    health_insurance_display = fields.Char(
        string='Health Insurances',
        compute='_compute_health_insurance_display',
        readonly=True
    )

    # Demographics - Combined display (like medical visit)
    demographics_display = fields.Char(
        string='Demographics',
        compute='_compute_demographics_display',
        readonly=True
    )

    # ==================== SURGERY DETAILS ====================
    surgery_plan = fields.Text(
        string='Surgery Plan',
        help='Doctor describes planned procedures - coordinator uses this to create SO',
        tracking=True
    )

    surgery_product_id = fields.Many2one(
        'product.product',
        string='Primary Surgery Product',
        help='Main product for SO - may have upsells added by coordinator',
        tracking=True
    )

    surgery_product_privilege_warning = fields.Boolean(
        compute='_compute_surgery_product_privilege_warning',
        string='Surgery Product Privilege Warning',
        help='Warning: Surgeon may not be authorized to perform this procedure'
    )

    surgeon_employee_id = fields.Many2one(
        'hr.employee',
        string='Surgeon',
        required=True,
        tracking=True
    )

    surgeon_user_id = fields.Many2one(
        'res.users',
        related='surgeon_employee_id.user_id',
        string='Surgeon User',
        store=True,
        readonly=True
    )

    surgery_date = fields.Date(
        string='Scheduled Surgery Date',
        tracking=True
    )

    surgery_location = fields.Selection([
        ('in_house', 'In-House'),
        ('external', 'External Surgical Center')
    ], default='in_house', string='Location', tracking=True)

    surgicenter_id = fields.Many2one(
        'res.partner',
        string='Surgical Center',
        domain=[('is_surgicenter', '=', True)],
        tracking=True
    )

    # ==================== WORKFLOW ====================
    stage_id = fields.Many2one(
        'surgery.stage',
        string='Stage',
        required=True,
        tracking=True,
        group_expand='_read_group_stage_ids',
        default=lambda self: self.env.ref(
            'hamarpea-odoo-surgery-coordination.stage_planning',
            raise_if_not_found=False
        )
    )

    coordinator_id = fields.Many2one(
        'res.users',
        string='Coordinator',
        tracking=True
    )

    # ==================== MEDICAL TRACK ====================
    medical_status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('review_needed', 'Review Needed'),
        ('confirmed', 'Confirmed')
    ], compute='_compute_medical_status', store=True, tracking=True, string='Medical Status')

    medical_confirmed = fields.Boolean(
        string='Medical Confirmed',
        readonly=True,
        tracking=True
    )

    medical_confirmed_by = fields.Many2one(
        'res.users',
        string='Confirmed By',
        readonly=True
    )

    medical_confirmed_date = fields.Datetime(
        string='Confirmed Date',
        readonly=True
    )

    medical_item_ids = fields.One2many(
        'surgery.medical.item',
        'surgery_case_id',
        string='Medical Checklist'
    )

    # ==================== FINANCIAL TRACK ====================
    financial_status = fields.Selection([
        ('incomplete', 'Incomplete'),
        ('pending', 'Pending Payment'),
        ('approved', 'Approved')
    ], compute='_compute_financial_status', store=True, tracking=True, string='Financial Status')

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        tracking=True
    )

    sale_order_state = fields.Selection(
        related='sale_order_id.state',
        string='SO Status',
        readonly=True
    )

    deposit_paid = fields.Boolean(
        string='Deposit Paid',
        compute='_compute_deposit_paid',
        store=True
    )

    financial_cleared = fields.Boolean(
        string='Financial Clearance Confirmed',
        tracking=True,
        help='Manually confirm financial clearance regardless of payment status'
    )

    financial_cleared_by = fields.Many2one(
        'res.users',
        string='Cleared By',
        readonly=True
    )

    financial_cleared_date = fields.Datetime(
        string='Cleared Date',
        readonly=True
    )

    # ==================== PAYMENT TRACKING ====================
    surgery_total = fields.Monetary(
        related='sale_order_id.amount_total',
        string='Surgery Total',
        readonly=True
    )

    # Expected amounts
    expected_client_amount = fields.Monetary(
        string='Client Expected',
        tracking=True,
        help='Amount expected from client (deposit)'
    )

    expected_surgicenter_amount = fields.Monetary(
        compute='_compute_expected_surgicenter',
        store=True,
        string='Surgicenter Expected',
        help='Amount to be paid via surgicenter (Surgery Total - Client - Insurance)'
    )

    # Received amounts
    client_received = fields.Monetary(
        compute='_compute_client_received',
        store=True,
        string='Client Received',
        help='Amount received from client (from paid invoices)'
    )

    insurance_received = fields.Monetary(
        string='Insurance Received',
        tracking=True,
        help='Amount received from insurance company'
    )

    surgicenter_received = fields.Monetary(
        string='Surgicenter Received',
        tracking=True,
        help='Amount received from surgicenter'
    )

    # Balance fields (computed)
    client_balance = fields.Monetary(
        compute='_compute_balances',
        string='Client Balance'
    )

    insurance_balance = fields.Monetary(
        compute='_compute_balances',
        string='Insurance Balance'
    )

    surgicenter_balance = fields.Monetary(
        compute='_compute_balances',
        string='Surgicenter Balance'
    )

    # Totals
    total_expected = fields.Monetary(
        compute='_compute_totals',
        string='Total Expected'
    )

    total_received = fields.Monetary(
        compute='_compute_totals',
        string='Total Received'
    )

    total_balance = fields.Monetary(
        compute='_compute_totals',
        string='Total Balance'
    )

    # ==================== INSURANCE ====================
    insurance_company_id = fields.Many2one(
        'res.partner',
        string='Insurance Company',
        domain=[('account_type', 'in', ['private_insurance', 'kupat_holim'])],
        tracking=True
    )

    is_contracted_insurance = fields.Boolean(
        compute='_compute_is_contracted_insurance',
        store=True,
        string='Direct Billing Available',
        help='Can clinic bill this insurance directly for this surgeon?'
    )

    insurance_privilege_warning = fields.Boolean(
        compute='_compute_insurance_privilege_warning',
        string='Insurance Privilege Warning',
        help='Warning: Surgeon may not have privileges with this insurance company'
    )

    insurance_claim_number = fields.Char(
        string='Claim Number',
        tracking=True
    )

    insurance_claim_status = fields.Selection([
        ('not_submitted', 'Not Submitted'),
        ('submitted', 'Submitted'),
        ('authorized', 'Authorized'),
        ('denied', 'Denied'),
        ('partial', 'Partial Approval')
    ], default='not_submitted', string='Claim Status', tracking=True)

    insurance_approved_amount = fields.Monetary(
        string='Approved Amount',
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    # ==================== SURGICAL CENTER COMMISSION ====================
    expected_surgeon_payment = fields.Monetary(
        compute='_compute_expected_surgeon_payment',
        store=True,
        string='Expected Payment from Surgical Center',
        help='Surgeon fee minus processing fee'
    )

    processing_fee_amount = fields.Monetary(
        compute='_compute_expected_surgeon_payment',
        store=True,
        string='Processing Fee Amount'
    )

    # ==================== AUDIT ====================
    audit_status = fields.Selection([
        ('incomplete', 'Incomplete'),
        ('complete', 'Complete')
    ], compute='_compute_audit_status', store=True, tracking=True, string='Audit Status')

    insurance_payment_confirmed = fields.Boolean(
        string='Insurance Payment Confirmed',
        tracking=True
    )

    insurance_payment_confirmed_by = fields.Many2one(
        'res.users',
        string='Confirmed By',
        readonly=True
    )

    insurance_payment_confirmed_date = fields.Datetime(
        string='Confirmed Date',
        readonly=True
    )

    surgicenter_payment_confirmed = fields.Boolean(
        string='Surgicenter Payment Confirmed',
        tracking=True
    )

    surgicenter_payment_confirmed_by = fields.Many2one(
        'res.users',
        string='Confirmed By',
        readonly=True
    )

    surgicenter_payment_confirmed_date = fields.Datetime(
        string='Confirmed Date',
        readonly=True
    )

    # ==================== GATEKEEPING ====================
    ready_for_scheduling = fields.Boolean(
        compute='_compute_ready_for_scheduling',
        store=True,
        string='Ready to Book Date',
        help='Financial clearance complete - can book surgery date'
    )

    ready_for_surgery = fields.Boolean(
        compute='_compute_ready_for_surgery',
        store=True,
        string='Ready for Surgery',
        help='Both medical and financial clearance complete'
    )

    # ==================== CALENDAR ====================
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Surgery Calendar Event'
    )

    # ==================== DRUG RESTRICTIONS ====================
    drug_restriction_ids = fields.Many2many(
        'surgery.drug.restriction',
        string='Drug Restrictions'
    )

    # ==================== COMPUTED FIELDS ====================

    @api.depends('partner_id.birthdate_date')
    def _compute_patient_age(self):
        for record in self:
            if record.partner_id.birthdate_date:
                today = fields.Date.today()
                record.patient_age = (today - record.partner_id.birthdate_date).days // 365
            else:
                record.patient_age = 0

    @api.depends('partner_id.kupat_holim_id', 'partner_id.private_insurance_ids')
    def _compute_health_insurance_display(self):
        """Combine Kupat Holim and Private Insurance into single display"""
        for record in self:
            parts = []

            # Add Kupat Holim or "No Kupa"
            if record.partner_id.kupat_holim_id:
                parts.append(record.partner_id.kupat_holim_id.name)
            else:
                parts.append('No Kupa')

            # Add Private Insurance or "No Private"
            if record.partner_id.private_insurance_ids:
                private_names = ', '.join(
                    record.partner_id.private_insurance_ids.mapped('name'))
                parts.append(private_names)
            else:
                parts.append('No Private')

            record.health_insurance_display = ' | '.join(parts)

    @api.depends('partner_id.birthdate_date', 'partner_id.gender')
    def _compute_demographics_display(self):
        """Combine DOB, Age, and Gender into single display"""
        from dateutil.relativedelta import relativedelta
        from datetime import datetime

        for record in self:
            parts = []

            # Date of Birth
            if record.partner_id.birthdate_date:
                dob_str = record.partner_id.birthdate_date.strftime('%d/%m/%Y')
                parts.append(dob_str)

                # Calculate Age
                today = datetime.now().date()
                delta = relativedelta(today, record.partner_id.birthdate_date)
                age_str = f"{delta.years}y {delta.months}m"
                parts.append(age_str)

            # Gender
            if record.partner_id.gender:
                gender_display = dict(record.partner_id._fields['gender'].selection).get(
                    record.partner_id.gender, '')
                parts.append(gender_display)

            record.demographics_display = ' | '.join(parts) if parts else ''

    @api.depends('sale_order_id.state', 'sale_order_id.invoice_ids.payment_state',
                 'insurance_company_id', 'insurance_claim_status', 'financial_cleared')
    def _compute_financial_status(self):
        for record in self:
            # Manual financial clearance overrides everything
            if record.financial_cleared:
                record.financial_status = 'approved'
            elif not record.sale_order_id or record.sale_order_id.state not in ['sale', 'done']:
                record.financial_status = 'incomplete'
            elif not record.deposit_paid:
                record.financial_status = 'pending'
            elif record.insurance_company_id and record.is_contracted_insurance and \
                 record.insurance_claim_status != 'authorized':
                record.financial_status = 'pending'
            else:
                record.financial_status = 'approved'

    @api.depends('sale_order_id.invoice_ids.payment_state')
    def _compute_deposit_paid(self):
        for record in self:
            if record.sale_order_id and record.sale_order_id.invoice_ids:
                # Check if any invoice has partial or full payment
                record.deposit_paid = any(
                    inv.payment_state in ['in_payment', 'paid', 'partial']
                    for inv in record.sale_order_id.invoice_ids
                )
            else:
                record.deposit_paid = False

    @api.depends('surgeon_employee_id.kupot_holim_ids', 'surgeon_employee_id.private_insurance_ids', 'insurance_company_id')
    def _compute_is_contracted_insurance(self):
        for record in self:
            if record.surgeon_employee_id and record.insurance_company_id:
                # Check if insurance company is in either Kupot Holim or Private Insurance lists
                record.is_contracted_insurance = (
                    record.insurance_company_id in record.surgeon_employee_id.kupot_holim_ids or
                    record.insurance_company_id in record.surgeon_employee_id.private_insurance_ids
                )
            else:
                record.is_contracted_insurance = False

    @api.depends('surgeon_employee_id.kupot_holim_ids', 'surgeon_employee_id.private_insurance_ids', 'insurance_company_id')
    def _compute_insurance_privilege_warning(self):
        """Show warning if surgeon doesn't have privileges with selected insurance"""
        for record in self:
            if record.insurance_company_id and record.surgeon_employee_id:
                # Warning if insurance is selected but surgeon doesn't have privileges
                has_privilege = (
                    record.insurance_company_id in record.surgeon_employee_id.kupot_holim_ids or
                    record.insurance_company_id in record.surgeon_employee_id.private_insurance_ids
                )
                record.insurance_privilege_warning = not has_privilege
            else:
                record.insurance_privilege_warning = False

    @api.depends('surgeon_employee_id.authorized_procedure_ids', 'surgery_product_id')
    def _compute_surgery_product_privilege_warning(self):
        """Show warning if surgeon is not authorized for selected procedure"""
        for record in self:
            if record.surgery_product_id and record.surgeon_employee_id:
                # Warning if procedure is selected but surgeon is not authorized
                has_privilege = record.surgery_product_id in record.surgeon_employee_id.authorized_procedure_ids
                record.surgery_product_privilege_warning = not has_privilege
            else:
                record.surgery_product_privilege_warning = False

    @api.depends('surgery_product_id.list_price', 'surgicenter_id.processing_fee_pct',
                 'surgery_location')
    def _compute_expected_surgeon_payment(self):
        for record in self:
            if record.surgery_location == 'external' and record.surgicenter_id and record.surgery_product_id:
                base_fee = record.surgery_product_id.list_price
                processing_pct = record.surgicenter_id.processing_fee_pct or 0
                record.processing_fee_amount = base_fee * (processing_pct / 100)
                record.expected_surgeon_payment = base_fee - record.processing_fee_amount
            else:
                if record.surgery_product_id:
                    record.expected_surgeon_payment = record.surgery_product_id.list_price
                else:
                    record.expected_surgeon_payment = 0
                record.processing_fee_amount = 0

    @api.depends('financial_status')
    def _compute_ready_for_scheduling(self):
        for record in self:
            record.ready_for_scheduling = (record.financial_status == 'approved')

    @api.depends('medical_confirmed', 'financial_status')
    def _compute_ready_for_surgery(self):
        for record in self:
            record.ready_for_surgery = (
                record.medical_confirmed and
                record.financial_status == 'approved'
            )

    # ==================== PAYMENT TRACKING COMPUTE ====================

    @api.depends('surgery_total', 'expected_client_amount', 'insurance_approved_amount', 'surgery_location')
    def _compute_expected_surgicenter(self):
        """Calculate expected surgicenter amount (only for external surgeries)"""
        for record in self:
            if record.surgery_location == 'external':
                record.expected_surgicenter_amount = (
                    (record.surgery_total or 0) -
                    (record.expected_client_amount or 0) -
                    (record.insurance_approved_amount or 0)
                )
            else:
                record.expected_surgicenter_amount = 0

    @api.depends('sale_order_id.invoice_ids.payment_state', 'sale_order_id.invoice_ids.amount_total',
                 'sale_order_id.invoice_ids.amount_residual')
    def _compute_client_received(self):
        """Calculate amount received from client based on paid invoices"""
        for record in self:
            total_received = 0
            if record.sale_order_id and record.sale_order_id.invoice_ids:
                for inv in record.sale_order_id.invoice_ids:
                    if inv.move_type == 'out_invoice':
                        # Amount paid = total - remaining
                        total_received += inv.amount_total - inv.amount_residual
            record.client_received = total_received

    @api.depends('expected_client_amount', 'client_received',
                 'insurance_approved_amount', 'insurance_received',
                 'expected_surgicenter_amount', 'surgicenter_received')
    def _compute_balances(self):
        """Calculate balance for each payment source"""
        for record in self:
            record.client_balance = (record.expected_client_amount or 0) - (record.client_received or 0)
            record.insurance_balance = (record.insurance_approved_amount or 0) - (record.insurance_received or 0)
            record.surgicenter_balance = (record.expected_surgicenter_amount or 0) - (record.surgicenter_received or 0)

    @api.depends('expected_client_amount', 'insurance_approved_amount', 'expected_surgicenter_amount',
                 'client_received', 'insurance_received', 'surgicenter_received',
                 'client_balance', 'insurance_balance', 'surgicenter_balance')
    def _compute_totals(self):
        """Calculate total expected, received, and balance"""
        for record in self:
            record.total_expected = (
                (record.expected_client_amount or 0) +
                (record.insurance_approved_amount or 0) +
                (record.expected_surgicenter_amount or 0)
            )
            record.total_received = (
                (record.client_received or 0) +
                (record.insurance_received or 0) +
                (record.surgicenter_received or 0)
            )
            record.total_balance = (
                (record.client_balance or 0) +
                (record.insurance_balance or 0) +
                (record.surgicenter_balance or 0)
            )

    @api.depends('insurance_balance', 'surgicenter_balance', 'surgery_location',
                 'insurance_payment_confirmed', 'surgicenter_payment_confirmed',
                 'insurance_company_id')
    def _compute_audit_status(self):
        """Audit is complete when all expected payments are received and confirmed"""
        for record in self:
            # Check if insurance payment is settled (if applicable)
            insurance_ok = True
            if record.insurance_company_id:
                insurance_ok = record.insurance_payment_confirmed or record.insurance_balance == 0

            # Check if surgicenter payment is settled (if external)
            surgicenter_ok = True
            if record.surgery_location == 'external':
                surgicenter_ok = record.surgicenter_payment_confirmed or record.surgicenter_balance == 0

            if insurance_ok and surgicenter_ok:
                record.audit_status = 'complete'
            else:
                record.audit_status = 'incomplete'

    @api.depends('medical_item_ids.status')
    def _compute_medical_status(self):
        for record in self:
            items = record.medical_item_ids
            if not items:
                record.medical_status = 'pending'
            elif record.medical_confirmed:
                record.medical_status = 'confirmed'
            elif any(item.status == 'received_abnormal' for item in items):
                record.medical_status = 'review_needed'
            elif all(item.status in ['received_normal', 'not_applicable'] for item in items if item.is_required):
                record.medical_status = 'review_needed'
            else:
                record.medical_status = 'in_progress'

    # ==================== ACTIONS ====================

    def action_confirm_medical(self):
        """Nurse or Doctor confirms medical clearance"""
        self.ensure_one()

        # Check that all required items are complete
        required_items = self.medical_item_ids.filtered(lambda i: i.is_required)
        incomplete_items = required_items.filtered(lambda i: i.status == 'awaited')

        if incomplete_items:
            raise UserError(
                "Cannot confirm medical clearance. The following required items are still awaited:\n" +
                "\n".join(f"- {item.test_type}" for item in incomplete_items)
            )

        self.write({
            'medical_confirmed': True,
            'medical_confirmed_by': self.env.user.id,
            'medical_confirmed_date': fields.Datetime.now()
        })
        self.message_post(
            body=f"Medical clearance confirmed by {self.env.user.name}"
        )
        return True

    def action_view_sale_order(self):
        """Open related sale order"""
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError("No Sale Order linked to this surgery case.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_sale_order(self):
        """Create a new sale order for this surgery case"""
        self.ensure_one()

        # Create the sale order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
        })

        # Link it to this surgery case
        self.sale_order_id = sale_order.id

        # Add surgery product if set
        if self.surgery_product_id:
            self.env['sale.order.line'].create({
                'order_id': sale_order.id,
                'product_id': self.surgery_product_id.id,
            })

        self.message_post(
            body=f"Sale Order {sale_order.name} created"
        )

        # Open the new sale order
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_confirm_financial(self):
        """Manually confirm financial clearance"""
        self.ensure_one()
        self.write({
            'financial_cleared': True,
            'financial_cleared_by': self.env.user.id,
            'financial_cleared_date': fields.Datetime.now()
        })
        self.message_post(
            body=f"Financial clearance confirmed by {self.env.user.name}"
        )
        return True

    def action_confirm_insurance_payment(self):
        """Confirm insurance payment received"""
        self.ensure_one()
        self.write({
            'insurance_payment_confirmed': True,
            'insurance_payment_confirmed_by': self.env.user.id,
            'insurance_payment_confirmed_date': fields.Datetime.now()
        })
        self.message_post(
            body=f"Insurance payment confirmed by {self.env.user.name}"
        )
        return True

    def action_confirm_surgicenter_payment(self):
        """Confirm surgicenter payment received"""
        self.ensure_one()
        self.write({
            'surgicenter_payment_confirmed': True,
            'surgicenter_payment_confirmed_by': self.env.user.id,
            'surgicenter_payment_confirmed_date': fields.Datetime.now()
        })
        self.message_post(
            body=f"Surgicenter payment confirmed by {self.env.user.name}"
        )
        return True

    def action_create_medical_checklist(self):
        """Manually create/recreate medical checklist items based on patient age"""
        self.ensure_one()

        # Delete existing items
        self.medical_item_ids.unlink()

        # Create new items
        self._create_medical_checklist_items()

        return True

    def _create_medical_checklist_items(self):
        """Create medical checklist items based on patient age"""
        self.ensure_one()

        # Standard items for all patients
        standard_items = [
            'blood_count',
            'chemistry',
            'clotting',
            'vitals',
            'medical_summary',
            'gp_consent'
        ]

        # Age-based items
        age = self.patient_age
        age_based_items = []

        if age >= 40:
            age_based_items.append('ecg')

        if age >= 60:
            age_based_items.append('chest_xray')

        all_items = standard_items + age_based_items

        # Create the items
        MedicalItem = self.env['surgery.medical.item']
        for test_type in all_items:
            MedicalItem.create({
                'surgery_case_id': self.id,
                'test_type': test_type,
                'status': 'awaited'
            })

    # ==================== LIFECYCLE ====================

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('surgery.case') or 'New'

        record = super().create(vals)

        # Auto-create medical checklist items
        record._create_medical_checklist_items()

        return record

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Show all stages in kanban view"""
        return stages.search([], order='sequence, id')
