# pitcar_custom/models/service_booking.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import pytz
from odoo.tools import ormcache

class ServiceBooking(models.Model):
    _name = 'pitcar.service.booking'
    _description = 'Service Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'booking_date desc, booking_time'
    @ormcache('self.id')
    def _get_booking_info(self):
        return {
            'name': self.name,
            'partner': self.partner_id.name,
            'formatted_time': self.formatted_time,
        }
    
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name),
                     ('partner_id.name', operator, name)]
        return self.search(domain + args, limit=limit).name_get()

    name = fields.Char(
        'Booking Reference', 
        required=True, 
        copy=False, 
        readonly=True, 
        default=lambda self: _('New'),
        tracking=True
    )
    
    partner_id = fields.Many2one(
        'res.partner', 
        string='Customer', 
        required=True,
        tracking=True,
        index=True
    )
    partner_car_id = fields.Many2one(
        'res.partner.car',
        string="Car to Service",
        domain="[('partner_id', '=', partner_id)]",
        required=True,
        tracking=True,
        index=True
    )
    partner_car_odometer = fields.Float(string="Odometer", tracking=True)
    
    service_category = fields.Selection([
        ('maintenance', 'Perawatan'),
        ('repair', 'Perbaikan')
    ], string="Kategori Servis", required=True, tracking=True)
    
    service_subcategory = fields.Selection([
        ('tune_up', 'Tune Up'),
        ('tune_up_addition', 'Tune Up + Addition'),
        ('periodic_service', 'Servis Berkala'),
        ('periodic_service_addition', 'Servis Berkala + Addition'),
        ('general_repair', 'General Repair'),
        ('oil_change', 'Ganti Oli'),
    ], string="Jenis Servis", required=True, tracking=True)

    booking_date = fields.Date('Booking Date', required=True, tracking=True, index=True)
    booking_time = fields.Float('Booking Time', required=True, tracking=True)
    formatted_time = fields.Char('Formatted Time', compute='_compute_formatted_time', store=True)
    
    service_advisor_id = fields.Many2many('pitcar.service.advisor', string="Service Advisors", tracking=True)
    sale_order_id = fields.Many2one('sale.order', string='Related Sale Order', readonly=True)
    notes = fields.Text('Notes')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('converted', 'Converted to SO'),  # Langsung ke converted, tanpa arrived
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, index=True)

    # Tambahkan field date_stop
    date_stop = fields.Date(
        string='End Date', 
        compute='_compute_date_stop', 
        store=True
    )

    # Queue tracking fields
    queue_number = fields.Integer('Queue Number', readonly=True)
    display_queue_number = fields.Char('Display Queue Number', readonly=True)
    is_arrived = fields.Boolean('Has Arrived', readonly=True)
    arrival_time = fields.Datetime('Arrival Time', readonly=True)
    estimated_wait_minutes = fields.Integer('Estimated Wait (minutes)', readonly=True)
    estimated_service_time = fields.Datetime('Estimated Service Time', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            # Format: BOOK/YYYYMM/XXXX
            vals['name'] = self.env['ir.sequence'].next_by_code('pitcar.service.booking') or _('New')
        return super().create(vals)

    @api.depends('booking_date')
    def _compute_date_stop(self):
        for record in self:
            if record.booking_date:
                record.date_stop = record.booking_date

    def action_link_to_sale_order(self):
      """Link booking with existing sale order"""
      self.ensure_one()
      if self.state != 'confirmed':
          raise ValidationError(_('Only confirmed bookings can be linked to sale orders'))
          
      if self.sale_order_id:
          raise ValidationError(_('This booking is already linked to a sale order'))
          
      return {
          'name': _('Link to Sale Order'),
          'type': 'ir.actions.act_window',
          'res_model': 'booking.link.sale.order.wizard',
          'view_mode': 'form',
          'target': 'new',
          'context': {'default_booking_id': self.id}
      }

    def action_convert_to_sale_order(self):
      self.ensure_one()
      if self.state not in ['confirmed', 'arrived']:
          raise ValidationError(_('Only confirmed or arrived bookings can be converted to sale orders'))
          
      if self.sale_order_id:
          raise ValidationError(_('This booking has already been converted to a sale order'))

      try:
          sale_order = self.env['sale.order'].create({
              'partner_id': self.partner_id.id,
              'partner_car_id': self.partner_car_id.id,
              'service_advisor_id': [(6, 0, self.service_advisor_id.ids)],
              'partner_car_odometer': self.partner_car_odometer,
              'service_category': self.service_category,
              'service_subcategory': self.service_subcategory,
              'is_booking': True,
              'booking_id': self.id,
              'origin': self.name,
          })

          # Convert booking lines dengan harga
          for line in self.booking_line_ids:
              self.env['sale.order.line'].create({
                  'order_id': sale_order.id,
                  'product_id': line.product_id.id,
                  'product_uom_qty': line.quantity,
                  'service_duration': line.service_duration,
                  'name': line.name,
                  'price_unit': line.price_unit,
                  'discount': line.discount,
                  'tax_id': [(6, 0, line.tax_ids.ids)],
              })

          # Update booking status
          self.write({
              'state': 'converted',
              'sale_order_id': sale_order.id
          })

          return {
              'type': 'ir.actions.act_window',
              'name': 'Sale Order',
              'res_model': 'sale.order',
              'res_id': sale_order.id,
              'view_mode': 'form',
              'target': 'current',
          }

      except Exception as e:
          raise ValidationError(_('Error converting booking to sale order: %s') % str(e))
        
    def action_confirm(self):
        """Confirm booking"""
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_('Only draft bookings can be confirmed'))
            record.write({'state': 'confirmed'})
        return True

    def action_mark_arrived(self):
      """Mark customer as arrived by linking to existing sale order"""
      self.ensure_one()
      if self.state != 'confirmed':
          raise ValidationError(_('Only confirmed bookings can be marked as arrived'))
          
      return {
          'name': _('Select Sale Order'),
          'type': 'ir.actions.act_window',
          'res_model': 'booking.link.sale.order.wizard',
          'view_mode': 'form',
          'target': 'new',
          'context': {
              'default_booking_id': self.id,
              # Filter SO hari ini
              'default_domain': [
                  ('create_date', '>=', fields.Date.today()),
                  ('create_date', '<', fields.Date.today() + timedelta(days=1)),
                  ('state', '!=', 'cancel')
              ]
          }
      }

    def action_cancel(self):
        """Cancel booking"""
        for record in self:
            if record.state in ['converted']:
                raise ValidationError(_('Cannot cancel booking that has been converted to sale order'))
            record.write({'state': 'cancelled'})
        return True
    
    @api.depends('booking_time')
    def _compute_formatted_time(self):
        for record in self:
            if record.booking_time:
                hours = int(record.booking_time)
                minutes = int((record.booking_time - hours) * 60)
                record.formatted_time = f"{hours:02d}:{minutes:02d}"
            else:
                record.formatted_time = False

    @api.constrains('booking_date')
    def _check_booking_date(self):
        for record in self:
            if record.booking_date < fields.Date.today():
                raise ValidationError(_('Booking date cannot be in the past'))

    @api.constrains('booking_time')
    def _check_booking_time(self):
        for record in self:
            if not 8.0 <= record.booking_time <= 17.0:
                raise ValidationError(_('Booking time must be between 08:00 and 17:00'))

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Clear car when customer changes"""
        if self.partner_id:
            self.partner_car_id = False

    booking_line_ids = fields.One2many(
      'pitcar.service.booking.line',
      'booking_id',
      string='Service Lines'
    )
    
    estimated_duration = fields.Float(
        string='Estimated Duration',
        compute='_compute_estimated_duration',
        store=True
    )

    @api.depends('booking_line_ids.service_duration')
    def _compute_estimated_duration(self):
        for booking in self:
            booking.estimated_duration = sum(booking.booking_line_ids.mapped('service_duration'))

     # Tambahkan fields untuk perhitungan total
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency',
        readonly=True,
        default=lambda self: self.env.company.currency_id
    )
    
    company_id = fields.Many2one(
        'res.company', 
        auto_join=True,  # Tambahkan auto_join untuk performa query
        default=lambda self: self.env.company
    )
    
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        store=True,
        compute='_compute_amounts',
        currency_field='currency_id'
    )
    
    amount_tax = fields.Monetary(
        string='Taxes',
        store=True,
        compute='_compute_amounts',
        currency_field='currency_id'
    )
    
    amount_total = fields.Monetary(
        string='Total',
        store=True,
        compute='_compute_amounts',
        currency_field='currency_id'
    )

    @api.depends('booking_line_ids.price_subtotal', 'booking_line_ids.price_tax')
    def _compute_amounts(self):
        """Compute the total amounts of the booking."""
        # Prefetch related records
        self.mapped('booking_line_ids.tax_ids').mapped('amount')
        for booking in self:
            amount_untaxed = sum(booking.booking_line_ids.mapped('price_subtotal'))
            amount_tax = sum(booking.booking_line_ids.mapped('price_tax'))
            booking.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

# pitcar_custom/models/service_booking.py
class ServiceBookingLine(models.Model):
    _name = 'pitcar.service.booking.line'
    _description = 'Service Booking Line'
    _order = 'sequence, id'

    booking_id = fields.Many2one('pitcar.service.booking', string='Booking Reference', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    product_id = fields.Many2one(
        'product.product', 
        string='Product/Service', 
        required=True,
        domain=[('type', 'in', ['service', 'product'])]  # Perbaikan di sini
    )
    name = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity', default=1.0)
    service_duration = fields.Float(string='Service Duration')

      # Fields untuk perhitungan harga
    price_unit = fields.Float(
        'Unit Price',
        required=True,
        digits='Product Price',
        default=0.0
    )
    
    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0
    )
    
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        domain=[('type_tax_use', '=', 'sale')]
    )
    
    price_subtotal = fields.Monetary(
        string='Subtotal',
        store=True,
        compute='_compute_amount',
        currency_field='currency_id'
    )
    
    price_tax = fields.Float(
        string='Total Tax',
        store=True,
        compute='_compute_amount'
    )
    
    price_total = fields.Monetary(
        string='Total',
        store=True,
        compute='_compute_amount',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        related='booking_id.currency_id',
        depends=['booking_id.currency_id'],
        store=True,
        string='Currency'
    )

    @api.depends('quantity', 'price_unit', 'tax_ids', 'discount')
    def _compute_amount(self):
        """Compute the amounts of the booking line."""
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(
                price,
                line.booking_id.currency_id,
                line.quantity,
                product=line.product_id,
                partner=line.booking_id.partner_id
            )
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
            
        # Lazy loading
        values = {
            'name': self.product_id.get_product_multiline_description_sale(),
            'price_unit': self.product_id.list_price,
            'service_duration': self.product_id.service_duration if self.product_id.type == 'service' else 0.0
        }
        
        if self.product_id.type == 'service':
            values['tax_ids'] = [(6, 0, self.product_id.taxes_id.filtered(
                lambda t: t.company_id == self.booking_id.company_id
            ).ids)]
            
        self.update(values)