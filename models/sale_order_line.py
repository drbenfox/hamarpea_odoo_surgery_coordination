from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_informational = fields.Boolean(
        string='Informational Only',
        help='This line appears on quotation for customer reference but will not be invoiced',
        copy=False
    )

    @api.depends('is_informational', 'product_uom_qty', 'qty_delivered', 'qty_invoiced')
    def _compute_qty_to_invoice(self):
        """Prevent informational lines from appearing as 'to invoice'"""
        super()._compute_qty_to_invoice()
        for line in self:
            if line.is_informational:
                line.qty_to_invoice = 0.0
                line.qty_invoiced = line.product_uom_qty

    def _prepare_invoice_line(self, **optional_values):
        """Skip informational lines when creating invoices"""
        if self.is_informational:
            return False
        return super()._prepare_invoice_line(**optional_values)
