from odoo import http, fields
from odoo.http import request, Response
import json
import pytz
from datetime import datetime, timedelta
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
import math

_logger = logging.getLogger(__name__)

class LeadTimePartController(http.Controller):
    def _validate_access(self, sale_order_id):
        """Validate user access and return sale order"""
        env = request.env
        sale_order = env['sale.order'].browse(sale_order_id)
        if not sale_order.exists():
            return None
        return sale_order

    def _format_datetime(self, dt):
        """Format datetime to Asia/Jakarta timezone"""
        if not dt:
            return None
        tz = pytz.timezone('Asia/Jakarta')
        local_dt = pytz.utc.localize(dt).astimezone(tz)
        return local_dt.strftime('%Y-%m-%d %H:%M:%S')

    def _format_time(self, dt):
        """Format time to HH:MM format"""
        if not dt:
            return None
        tz = pytz.timezone('Asia/Jakarta')
        local_dt = pytz.utc.localize(dt).astimezone(tz)
        return local_dt.strftime('%H:%M')

    def _parse_time(self, time_str):
        """Parse time string to UTC datetime"""
        try:
            tz = pytz.timezone('Asia/Jakarta')
            today = datetime.now(tz).date()
            local_dt = tz.localize(datetime.combine(today, datetime.strptime(time_str, '%H:%M').time()))
            return local_dt.astimezone(pytz.UTC).replace(tzinfo=None)
        except ValueError:
            raise ValidationError("Invalid time format. Please use HH:MM format")

    def _get_purchase_details(self, purchase):
      """Get formatted purchase details"""
      if not purchase:
          return {}

      return {
        'id': purchase.id,
        'name': f'PP{str(purchase.id).zfill(5)}',
        # Add new fields
        'purchase_type': purchase.purchase_type,
        'estimated_completeness': purchase.estimated_completeness,
        'actual_completeness': purchase.actual_completeness,
        'sale_order': {
            'id': purchase.sale_order_id.id,
            'name': purchase.sale_order_id.name
        },
        'customer': {
            'id': purchase.partner_id.id,
            'name': purchase.partner_id.name
        },
        'car': {
            'id': purchase.partner_car_id.id,
            'brand': purchase.partner_car_id.brand.name if purchase.partner_car_id.brand else None,
            'type': purchase.partner_car_id.brand_type.name if purchase.partner_car_id.brand_type else None,
            'plate': purchase.partner_car_id.number_plate
        },
        'timestamps': {
            'departure': self._format_datetime(purchase.departure_time),
            'return': self._format_datetime(purchase.return_time),
            'estimated_departure': self._format_datetime(purchase.estimated_departure),
            'estimated_return': self._format_datetime(purchase.estimated_return)
        },
        'duration': {
            'hours': purchase.duration,
            'display': purchase.duration_display,
            'estimated_hours': purchase.estimated_duration,
            'estimated_display': self._format_duration(purchase.estimated_duration)
        },
        'partman': {
            'id': purchase.partman_id.id,
            'name': purchase.partman_id.name
        } if purchase.partman_id else None,
        'review_type': purchase.review_type,
        'notes': purchase.notes,
        'state': purchase.state
      }
    
    @http.route('/web/part-purchase/available-orders', type='json', auth='user', methods=['POST'])
    def get_available_orders(self, **kw):
        """Get available sale orders for part purchase"""
        try:
            # Extract parameters
            page = int(kw.get('page', 1))
            limit = int(kw.get('limit', 20))
            search_query = kw.get('search', '').strip()
            filter_type = kw.get('filter', 'all')  # all, need_part, active, completed
            
            # Improved base domain
            domain = [
                ('sa_mulai_penerimaan', '!=', False),  # Sudah mulai penerimaan
                ('car_arrival_time', '!=', False),  # Mobil sudah masuk
                ('fo_unit_keluar', '=', False),  # Mobil belum keluar
                ('controller_selesai' , '=', False),  # Servis belum selesai
                ('need_part_purchase', '=', 'yes'),  # Sudah request part
                ('state', 'not in', ['cancel', 'done'])  # Order aktif
            ]
            
            # Add search
            if search_query:
                domain = ['&'] + domain + ['|', '|', '|', '|',
                    ('name', 'ilike', search_query),
                    ('partner_id.name', 'ilike', search_query),
                    ('partner_car_id.number_plate', 'ilike', search_query),
                    ('generated_mechanic_team', 'ilike', search_query),
                    ('service_advisor_id.name', 'ilike', search_query)
                ]

            # Add filter
            if filter_type == 'need_part':
                domain.append(('need_part_purchase', '=', 'yes'))
            elif filter_type == 'active':
                domain.append(('part_purchase_ids.state', 'in', ['draft', 'departed']))
            elif filter_type == 'completed':
                domain.extend([
                    ('need_part_purchase', '=', 'yes'),
                    ('part_purchase_status', '=', 'completed')
                ])

            # Get total count for pagination
            SaleOrder = request.env['sale.order']
            total_count = SaleOrder.search_count(domain)
            total_pages = math.ceil(total_count / limit)
            
            # Get paginated records
            offset = (page - 1) * limit
            orders = SaleOrder.search(domain, limit=limit, offset=offset, 
                                    order='create_date desc')

            # Format response
            result = []
            for order in orders:
                 # Hitung status part request
                has_pending_items = False
                has_late_responses = False
                has_part_request = bool(order.part_request_items_ids)

                if has_part_request:
                    pending_items = order.part_request_items_ids.filtered(lambda x: not x.is_fulfilled)
                    late_responses = order.part_request_items_ids.filtered(lambda x: x.is_response_late)
                    has_pending_items = bool(pending_items)
                    has_late_responses = bool(late_responses)
                result.append({
                    'id': order.id,
                    'name': order.name,
                    'customer': {
                        'id': order.partner_id.id,
                        'name': order.partner_id.name
                    },
                    'car': {
                        'brand': order.partner_car_brand.name,
                        'type': order.partner_car_brand_type.name,
                        'plate': order.partner_car_id.number_plate
                    },
                    'need_part': order.need_part_purchase == 'yes',
                    'request_info': {
                        'request_time': self._format_datetime(order.part_request_time),
                        'notes': order.part_request_notes,
                        'status': order.part_purchase_status,
                        'total_items': order.total_requested_items,
                        'fulfilled_items': order.total_fulfilled_items,
                        'all_fulfilled': order.all_items_fulfilled
                    },
                    'items': [{
                        'id': item.id,
                        'product': {
                            'id': item.product_id.id,
                            'name': item.part_name,
                            'part_number': item.part_number
                        },
                        'quantity': item.quantity,
                        'notes': item.notes,
                        'status': {
                            'is_fulfilled': item.is_fulfilled,
                            'response_time': self._format_datetime(item.response_time),
                            'response_deadline': self._format_datetime(item.response_deadline),
                            'is_response_late': item.is_response_late
                        },
                        'response': {
                            'alternative_part': item.alternative_part,
                            'estimated_cost': item.estimated_cost,
                            'estimated_arrival': self._format_datetime(item.estimated_arrival),
                            'notes': item.response_notes
                        } if item.response_time else None
                    } for item in order.part_request_items_ids],
                    'part_purchase_status': {
                        'code': order.part_purchase_status,
                        'text': dict(order._fields['part_purchase_status'].selection).get(
                            order.part_purchase_status
                        )
                    },
                    'mechanic': order.generated_mechanic_team,
                    'service_advisor': ', '.join(order.service_advisor_id.mapped('name')),
                    'part_purchases': [{
                        'id': pp.id,
                        'name': pp.name,
                        'departure': self._format_datetime(pp.departure_time),
                        'return': self._format_datetime(pp.return_time),
                        'duration': pp.duration_display,
                        'state': pp.state,
                        'partman': pp.partman_id.name if pp.partman_id else None
                    } for pp in order.part_purchase_ids],
                    'timestamps': {
                        'reception': self._format_datetime(order.sa_jam_masuk),
                        'service_start': self._format_datetime(order.controller_mulai_servis),
                        'pkb_printed': self._format_datetime(order.sa_cetak_pkb)
                    }
                })

            return {
                'status': 'success',
                'data': {
                    'rows': result,
                    'pagination': {
                        'total_items': total_count,
                        'total_pages': total_pages,
                        'current_page': page,
                        'items_per_page': limit,
                        'has_next': page < total_pages,
                        'has_previous': page > 1
                    },
                    # Di endpoint get_available_orders
                    'summary': {
                        'total_orders': SaleOrder.search_count(domain),  # Total dengan domain dasar
                        'not_purchased': SaleOrder.search_count([
                            ('need_part_purchase', '=', 'yes'),
                            ('part_purchase_ids', '=', False),  # Belum ada pembelian sama sekali
                            ('fo_unit_keluar', '=', False),     # Mobil belum keluar
                            ('controller_selesai', '=', False)   # Servis belum selesai
                        ]),
                        'in_progress': SaleOrder.search_count([
                            ('need_part_purchase', '=', 'yes'),
                            ('part_purchase_ids.state', '=', 'departed'),  # Ada pembelian yang sedang berjalan
                            ('fo_unit_keluar', '=', False),
                            ('controller_selesai', '=', False)
                        ]),
                        'purchased': SaleOrder.search_count([
                            ('need_part_purchase', '=', 'yes'),
                            ('part_purchase_ids.state', '=', 'returned'),  # Ada pembelian yang sudah selesai
                            ('fo_unit_keluar', '=', False),
                            ('controller_selesai', '=', False)
                        ]),
                    }
                }
            }

        except Exception as e:
            _logger.error(f"Error in get_available_orders: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
        
    @http.route('/web/part-request/<int:item_id>/respond', type='json', auth='user')
    def respond_to_request(self, item_id, **kw):
        """Tim Part memberikan response untuk request part"""
        try:
            item = request.env['sale.order.part.item'].browse(item_id)
            if not item.exists():
                return {'status': 'error', 'message': 'Item not found'}

            order = item.sale_order_id
            if order.part_purchase_status not in ['pending', 'in_progress']:
                return {'status': 'error', 'message': 'Invalid order status'}

            # Extract response data
            response_data = kw.get('response', {})
            values = {
                'response_time': fields.Datetime.now(),
                'alternative_part': response_data.get('alternative_part'),
                'estimated_cost': response_data.get('estimated_cost'),
                'estimated_arrival': response_data.get('estimated_arrival'),
                'response_notes': response_data.get('response_notes')
            }
            
            _logger.info(f"Writing values to item {item_id}: {values}")
            item.write(values)

            return {
                'status': 'success',
                'data': {
                    'item': {
                        'id': item.id,
                        'response_time': item.response_time,
                        'is_response_late': item.is_response_late,
                        'response': {
                            'alternative_part': item.alternative_part or False,
                            'estimated_cost': item.estimated_cost or 0.0,
                            'estimated_arrival': item.estimated_arrival or False,
                            'notes': item.response_notes or False
                        }
                    },
                    'order_status': {
                        'total_items': order.total_requested_items,
                        'fulfilled_items': order.total_fulfilled_items,
                        'all_fulfilled': order.all_items_fulfilled,
                        'status': order.part_purchase_status
                    }
                }
            }

        except Exception as e:
            _logger.error(f"Error responding to part request: {str(e)}")
            return {'status': 'error', 'message': str(e)}


    @http.route('/web/part-request/respond-batch', type='json', auth='user')
    def respond_to_requests_batch(self, items=None, **kw):
        try:
            _logger.info(f"Starting batch response with items: {items}")
            if not items:
                return {'status': 'error', 'message': 'No items provided'}

            PartItem = request.env['sale.order.part.item']
            results = []
            now = fields.Datetime.now()
            
            for item_data in items:
                try:
                    item_id = item_data.get('id')
                    _logger.info(f"Processing item ID: {item_id}")
                    
                    if not item_id:
                        _logger.warning("Skipping - No item ID")
                        continue
                        
                    item = PartItem.browse(item_id)
                    if not item.exists():
                        _logger.warning(f"Skipping - Item {item_id} not found")
                        continue

                    # Validate required fields
                    if not item_data.get('estimated_cost'):
                        _logger.warning(f"Skipping item {item_id} - Missing estimated cost")
                        continue

                    # Konversi estimated_arrival dari Asia/Jakarta ke UTC
                    estimated_arrival = False
                    if item_data.get('estimated_arrival'):
                        try:
                            # Parse datetime string
                            local_tz = pytz.timezone('Asia/Jakarta')
                            datetime_str = item_data.get('estimated_arrival')
                            
                            # Handle different datetime formats
                            if 'T' in datetime_str:
                                local_dt = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
                            else:
                                local_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                                
                            # Lokalisasi ke timezone Asia/Jakarta dan konversi ke UTC
                            local_dt = local_tz.localize(local_dt)
                            utc_dt = local_dt.astimezone(pytz.UTC)
                            estimated_arrival = utc_dt.replace(tzinfo=None)  # Remove tzinfo for Odoo
                            
                            _logger.info(f"Converted estimated_arrival: {estimated_arrival}")
                        except Exception as e:
                            _logger.error(f"Error converting datetime: {str(e)}")
                            estimated_arrival = False

                    # Update values dengan waktu yang sudah dikonversi
                    values = {
                        'response_time': now,
                        'state': 'responded',
                        'alternative_part': item_data.get('alternative_part'),
                        'estimated_cost': item_data.get('estimated_cost'),
                        'estimated_arrival': estimated_arrival,
                        'response_notes': item_data.get('notes')
                    }
                    
                    _logger.info(f"Writing values for item {item_id}: {values}")
                    item.write(values)
                    
                    # Force recompute is_response_late
                    item.invalidate_cache(['is_response_late'])
                    item._compute_is_response_late()
                    
                    result = {
                        'id': item.id,
                        'status': 'success',
                        'data': {
                            'response_time': item.response_time,
                            'is_response_late': item.is_response_late,
                            'state': item.state,
                            'response': {
                                'alternative_part': item.alternative_part or False,
                                'estimated_cost': item.estimated_cost or 0.0,
                                'estimated_arrival': self._format_datetime(item.estimated_arrival),
                                'notes': item.response_notes or False
                            }
                        }
                    }
                    _logger.info(f"Result for item {item_id}: {result}")
                    results.append(result)
                    
                except Exception as item_error:
                    _logger.error(f"Error processing item {item_id}: {str(item_error)}", exc_info=True)
                    continue

            response = {
                'status': 'success',
                'data': {
                    'results': results,
                    'failed': len(items) - len(results)
                }
            }
            _logger.info(f"Final response: {response}")
            return response

        except Exception as e:
            _logger.error("Error in batch response", exc_info=True)
            return {'status': 'error', 'message': str(e)}
        
    def _validate_items(self, items_data):
        """Validate items data for batch operations"""
        if not isinstance(items_data, list):
            return False, "Items data must be a list"
            
        required_fields = {'id', 'is_fulfilled'}
        for item in items_data:
            if not all(field in item for field in required_fields):
                return False, f"Missing required fields: {required_fields}"
        return True, ""

    def _batch_items(self, items, batch_size=100):
        """Helper to process items in batches"""
        for i in range(0, len(items), batch_size):
            yield items[i:i + batch_size]

    @http.route('/web/part-purchase/order/<int:order_id>/toggle-need-part', type='json', auth='user', methods=['POST'])
    def toggle_need_part(self, order_id, **kw):
        """Toggle need part purchase flag for sale order"""
        try:
            order = request.env['sale.order'].browse(order_id)
            if not order.exists():
                return {
                    'status': 'error',
                    'message': 'Sale order not found'
                }

            # Toggle flag
            new_value = 'no' if order.need_part_purchase == 'yes' else 'yes'
            order.write({'need_part_purchase': new_value})

            return {
                'status': 'success',
                'data': {
                    'id': order.id,
                    'need_part_purchase': new_value,
                    'status': order.part_purchase_status
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }


    @http.route('/web/part-purchase/table', type='json', auth='user', methods=['POST'])
    def get_table_data(self, **kw):
        """Get paginated part purchase data with filtering"""
        try:
            # Extract parameters
            page = int(kw.get('page', 1))
            limit = int(kw.get('limit', 20))
            search_query = kw.get('search', '').strip()
            filter_type = kw.get('filter', 'all')
            sort_by = kw.get('sort_by', 'id')
            sort_order = kw.get('sort_order', 'desc')

            domain = []
            
            # Add search conditions
            if search_query:
                search_domain = ['|', '|', '|', '|',
                    ('name', 'ilike', search_query),
                    ('sale_order_id.name', 'ilike', search_query),
                    ('partner_id.name', 'ilike', search_query),
                    ('partner_car_id.number_plate', 'ilike', search_query),
                    ('partman_id.name', 'ilike', search_query)
                ]
                domain.extend(search_domain)

            # Add filter conditions
            if filter_type != 'all':
                domain.append(('state', '=', filter_type))

            # Prepare sorting
            order_mapping = {
                'id': 'id',
                'date': 'departure_time',
                'customer': 'partner_id',
                'status': 'state',
                'duration': 'duration'
            }
            sort_field = order_mapping.get(sort_by, 'id')
            order = f'{sort_field} {sort_order}'

            # Get records count
            PartPurchase = request.env['part.purchase.leadtime']
            total_count = PartPurchase.search_count(domain)
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

            # Get paginated records
            offset = (page - 1) * limit
            # purchases = PartPurchase.search(domain, limit=limit, offset=offset, order=order)
            purchases = PartPurchase.sudo().search(domain, limit=limit, offset=offset, order=order)

            # Format response data
            rows = []
            for purchase in purchases:
                # rows.append(self._get_purchase_details(purchase))
                rows.append(self._get_purchase_details(purchase.sudo()))

            # Get summary statistics
            summary = {
                'total': PartPurchase.search_count([]),
                'departed': PartPurchase.search_count([('state', '=', 'departed')]),
                'returned': PartPurchase.search_count([('state', '=', 'returned')]),
                'cancelled': PartPurchase.search_count([('state', '=', 'cancel')]),
                'avg_duration': PartPurchase.search_read([
                    ('state', '=', 'returned'),
                    ('duration', '>', 0)
                ], ['duration'])
            }

            if summary['avg_duration']:
                total_duration = sum(record['duration'] for record in summary['avg_duration'])
                summary['avg_duration'] = total_duration / len(summary['avg_duration'])
            else:
                summary['avg_duration'] = 0

            return {
                'status': 'success',
                'data': {
                    'rows': rows,
                    'pagination': {
                        'total_items': total_count,
                        'total_pages': total_pages,
                        'current_page': page,
                        'items_per_page': limit
                    },
                    'summary': summary
                }
            }

        except Exception as e:
            _logger.error(f"Error in get_table_data: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    # Ubah method ini di class LeadTimePartController
    # Di LeadTimePartController
    @http.route('/web/part-purchase/detail', type='json', auth='user', methods=['POST'])
    def get_purchase_detail(self, **kw):
        """Get detailed part purchase information"""
        try:
            _logger.info(f"Received kw: {kw}")  # Debug log untuk melihat isi kw
            
            # Cek langsung dari kw
            purchase_id = kw.get('purchase_id')
            
            # Jika tidak ada di kw langsung, cek di params
            if not purchase_id:
                params = kw.get('params', {})
                purchase_id = params.get('purchase_id')
                
            _logger.info(f"Found purchase_id: {purchase_id}")  # Debug log purchase_id

            if not purchase_id:
                return {
                    'status': 'error',
                    'message': 'Purchase ID is required'
                }

            purchase = request.env['part.purchase.leadtime'].browse(int(purchase_id))
            if not purchase.exists():
                return {
                    'status': 'error',
                    'message': 'Purchase record not found'
                }

            details = self._get_purchase_details(purchase)
            _logger.info(f"Purchase details: {details}")  # Debug log hasil

            return {
                'status': 'success',
                'data': details
            }

        except Exception as e:
            _logger.error(f"Error in get_purchase_detail: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/web/part-purchase/create', type='json', auth='user', methods=['POST'])
    def create_purchase(self, **kw):
        """Create new part purchase record"""
        try:
            # Ambil params langsung dari kw karena kita pakai type='json'
            sale_order_id = kw.get('sale_order_id')
            partman_id = kw.get('partman_id')
            
            # Validasi required fields
            if not sale_order_id or not partman_id:
                return {
                    'status': 'error',
                    'message': 'sale_order_id and partman_id are required'
                }
            
            # Add purchase type validation
            purchase_type = kw.get('purchase_type', 'part')  # Default to 'part'
            if purchase_type not in ['part', 'tool']:
                return {
                    'status': 'error',
                    'message': 'Invalid purchase type. Must be either "part" or "tool"'
                }

            # Parse time inputs
            est_departure_str = kw.get('estimated_departure')
            est_return_str = kw.get('estimated_return')
            
            if not est_departure_str or not est_return_str:
                return {
                    'status': 'error',
                    'message': 'Estimated departure and return times are required'
                }

            try:
                est_departure = self._parse_time(est_departure_str)
                est_return = self._parse_time(est_return_str)
            except ValueError as e:
                return {
                    'status': 'error',
                    'message': f'Invalid time format: {str(e)}. Please use HH:mm format.'
                }
            
            # Calculate estimated duration
            estimated_duration = 0
            if est_departure and est_return:
                if est_return < est_departure:
                    est_return += timedelta(days=1)  # Asumsi kembali di hari berikutnya
                time_diff = est_return - est_departure
                estimated_duration = time_diff.total_seconds() / 3600  # Convert to hours

            # Prepare values for creation
            values = {
                'sale_order_id': int(sale_order_id),
                'partman_id': int(partman_id),
                'purchase_type': purchase_type,
                'review_type': kw.get('review_type'),
                'notes': kw.get('notes'),
                'estimated_departure': est_departure,
                'estimated_return': est_return,
                'estimated_duration': estimated_duration
            }

            purchase = request.env['part.purchase.leadtime'].create(values)
            
            return {
                'status': 'success',
                'data': self._get_purchase_details(purchase),
                'message': 'Part purchase record created successfully'
            }

        except Exception as e:
            _logger.error(f"Error in create_purchase: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _parse_time(self, time_str):
      """Parse time string to datetime with correct timezone
      Args:
          time_str (str): Time string in HH:mm format
      Returns:
          datetime: Datetime object in UTC
      """
      if not time_str:
          raise ValueError("Time string cannot be empty")
          
      try:
          # Parse input time
          hours, minutes = map(int, time_str.split(':'))
          if not (0 <= hours <= 23 and 0 <= minutes <= 59):
              raise ValueError("Hours must be 0-23 and minutes must be 0-59")
              
          # Get current date in Asia/Jakarta timezone
          tz = pytz.timezone('Asia/Jakarta')
          local_now = fields.Datetime.now().astimezone(tz)
          
          # Create local datetime
          local_dt = local_now.replace(
              hour=hours,
              minute=minutes,
              second=0,
              microsecond=0
          )
          
          # Convert to UTC for storage
          utc_dt = local_dt.astimezone(pytz.UTC)
          
          return utc_dt.replace(tzinfo=None)  # Remove tzinfo for Odoo compatibility
          
      except ValueError:
          raise ValueError("Invalid time format. Please use HH:mm format")

    @http.route('/web/part-purchase/<int:purchase_id>/depart', type='json', auth='user', methods=['POST'])
    def record_departure(self, purchase_id, **kw):
        """Record part purchase departure"""
        try:
            # Get parameters from kw
            start_time = kw.get('startTime')  # Format HH:MM
            notes = kw.get('notes')

            purchase = request.env['part.purchase.leadtime'].browse(purchase_id)
            if not purchase.exists():
                return {
                    'status': 'error',
                    'message': 'Purchase record not found'
                }

            if purchase.state != 'draft':
                return {
                    'status': 'error', 
                    'message': 'Invalid state for departure'
                }

            values = {}
            if start_time:
                values['departure_time'] = self._parse_time(start_time)
            else:
                values['departure_time'] = fields.Datetime.now()

            if notes:
                values['notes'] = notes

            values['state'] = 'departed'
            purchase.write(values)

            # Log activity
            msg = f"""
                <p><strong>Partman berangkat</strong></p>
                <ul>
                    <li>Waktu: {self._format_datetime(values['departure_time'])}</li>
                    {f'<li>Catatan: {notes}</li>' if notes else ''}
                </ul>
            """
            purchase.message_post(body=msg)
            
            return {
                'status': 'success',
                'data': self._get_purchase_details(purchase),
                'message': 'Departure recorded successfully'
            }

        except Exception as e:
            _logger.error(f"Error recording departure: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/web/part-purchase/<int:purchase_id>/return', type='json', auth='user', methods=['POST'])
    def record_return(self, purchase_id, **kw):
        """Record part purchase return"""
        try:
            # Get parameters from kw
            end_time = kw.get('endTime')  # Format HH:MM
            notes = kw.get('notes')
            actual_completeness = kw.get('actual_completeness')  # New field

            purchase = request.env['part.purchase.leadtime'].browse(purchase_id)
            if not purchase.exists():
                return {
                    'status': 'error',
                    'message': 'Purchase record not found'
                }

            if purchase.state != 'departed':
                return {
                    'status': 'error',
                    'message': 'Invalid state for return'
                }

            values = {}
            if end_time:
                values['return_time'] = self._parse_time(end_time)
            else:
                values['return_time'] = fields.Datetime.now()

            if notes:
                values['notes'] = notes

             # Add actual completeness
            if actual_completeness is not None:
                values['actual_completeness'] = float(actual_completeness)

            values['state'] = 'returned'
            purchase.write(values)

            # Log activity
            msg = f"""
                <p><strong>Partman kembali</strong></p>
                <ul>
                    <li>Waktu: {self._format_datetime(values['return_time'])}</li>
                    <li>Tipe: {purchase.purchase_type}</li>
                    <li>Kecocokan: {actual_completeness}%</li>
                    {f'<li>Catatan: {notes}</li>' if notes else ''}
                    <li>Durasi: {purchase.duration_display}</li>
                </ul>
            """
            purchase.message_post(body=msg)

            return {
                'status': 'success',
                'data': self._get_purchase_details(purchase),
                'message': 'Return recorded successfully'
            }

        except Exception as e:
            _logger.error(f"Error recording return: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/web/part-purchase/<int:purchase_id>/cancel', type='json', auth='user', methods=['POST'])
    def cancel_purchase(self, purchase_id, **kw):
        """Cancel part purchase"""
        try:
            notes = kw.get('notes')

            purchase = request.env['part.purchase.leadtime'].browse(purchase_id)
            if not purchase.exists():
                return {
                    'status': 'error',
                    'message': 'Purchase record not found'
                }

            if purchase.state in ['returned', 'cancel']:
                return {
                    'status': 'error',
                    'message': 'Cannot cancel completed or already cancelled purchase'
                }

            values = {
                'state': 'cancel'
            }
            if notes:
                values['notes'] = notes

            purchase.write(values)

            # Log activity
            msg = f"""
                <p><strong>Pembelian dibatalkan</strong></p>
                <ul>
                    <li>Waktu: {self._format_datetime(fields.Datetime.now())}</li>
                    {f'<li>Alasan: {notes}</li>' if notes else ''}
                </ul>
            """
            purchase.message_post(body=msg)

            return {
                'status': 'success',
                'data': self._get_purchase_details(purchase),
                'message': 'Purchase cancelled successfully'
            }

        except Exception as e:
            _logger.error(f"Error cancelling purchase: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/web/part-purchase/statistics', type='json', auth='user', methods=['POST'])
    def get_statistics(self, **kw):
        """Get comprehensive statistics for part purchases"""
        try:
            # Extract parameters
            params = kw.get('params', {})
            date_range = params.get('date_range', 'today')  # today, week, month, year
            start_date = params.get('start_date')
            end_date = params.get('end_date')

            PartPurchase = request.env['part.purchase.leadtime']
            SaleOrderPartItem = request.env['sale.order.part.item']
            
            # Build date domain
            domain = []
            if date_range == 'today':
                today = fields.Date.today()
                domain = [('create_date', '>=', today)]
            elif date_range == 'week':
                week_start = fields.Date.today() - timedelta(days=fields.Date.today().weekday())
                domain = [('create_date', '>=', week_start)]
            elif date_range == 'month':
                month_start = fields.Date.today().replace(day=1)
                domain = [('create_date', '>=', month_start)]
            elif date_range == 'custom' and start_date and end_date:
                domain = [
                    ('create_date', '>=', start_date),
                    ('create_date', '<=', end_date)
                ]

            # 1. Statistik Response Part Request
            part_request_domain = domain.copy()
            part_requests = SaleOrderPartItem.search(part_request_domain)
            responded_requests = part_requests.filtered(lambda r: r.response_time)
            
            total_requests = len(part_requests)
            total_responded = len(responded_requests)
            
            # Hitung response time rata-rata
            avg_response_time = 0
            on_time_responses = 0
            if responded_requests:
                response_times = []
                for request in responded_requests:
                    time_diff = (request.response_time - request.create_date).total_seconds() / 60  # dalam menit
                    response_times.append(time_diff)
                    if time_diff <= 15:  # Response dalam 15 menit
                        on_time_responses += 1
                avg_response_time = sum(response_times) / len(response_times)

            # 2. Statistik Pemenuhan Request (Fulfillment)
            fulfilled_requests = part_requests.filtered(lambda r: r.is_fulfilled)
            total_fulfilled = len(fulfilled_requests)

            # 3. Statistik Pembelian berdasarkan tipe
            purchase_stats = {
                'part': {
                    'total': PartPurchase.search_count(domain + [('purchase_type', '=', 'part')]),
                    'success': PartPurchase.search_count(domain + [
                        ('purchase_type', '=', 'part'),
                        ('state', '=', 'returned'),
                        ('actual_completeness', '>=', 90)  # Dianggap sukses jika completeness >= 90%
                    ])
                },
                'tool': {
                    'total': PartPurchase.search_count(domain + [('purchase_type', '=', 'tool')]),
                    'success': PartPurchase.search_count(domain + [
                        ('purchase_type', '=', 'tool'),
                        ('state', '=', 'returned'),
                        ('actual_completeness', '>=', 90)
                    ])
                }
            }


            # Basic stats with date filter
            total_purchases = PartPurchase.search_count(domain)
            departed_purchases = PartPurchase.search_count(domain + [('state', '=', 'departed')])
            completed_purchases = PartPurchase.search_count(domain + [('state', '=', 'returned')])
            cancelled_purchases = PartPurchase.search_count(domain + [('state', '=', 'cancel')])
            
            # Duration stats
            completed_records = PartPurchase.search_read(
                domain + [
                    ('state', '=', 'returned'),
                    ('duration', '>', 0)
                ], 
                ['duration']
            )
            
            avg_duration = 0
            if completed_records:
                total_duration = sum(record['duration'] for record in completed_records)
                avg_duration = total_duration / len(completed_records)

            # Partman performance
            partman_stats = PartPurchase.read_group(
                domain + [('state', '=', 'returned')],
                ['partman_id', 'duration:avg'],
                ['partman_id']
            )

            # Format time periods for display
            period_info = {
                'start': self._format_datetime(fields.Datetime.from_string(start_date)) if start_date else None,
                'end': self._format_datetime(fields.Datetime.from_string(end_date)) if end_date else None,
                'range': date_range
            }

            # Add type-specific stats
            part_purchases = PartPurchase.search_count(domain + [('purchase_type', '=', 'part')])
            tool_purchases = PartPurchase.search_count(domain + [('purchase_type', '=', 'tool')])
            
            # Add completeness stats
            completeness_stats = PartPurchase.read_group(
                domain + [('state', '=', 'returned')],
                ['purchase_type', 'actual_completeness:avg'],
                ['purchase_type']
            )

            return {
                'status': 'success',
                'data': {
                    'period': period_info,
                    'summary': {
                        'total_purchases': total_purchases,
                        'departed_purchases': departed_purchases,
                        'completed_purchases': completed_purchases,
                        'cancelled_purchases': cancelled_purchases,

                        # Response stats
                        'request_stats': {
                            'total_requests': total_requests,
                            'responded_requests': total_responded,
                            'response_rate': (total_responded / total_requests * 100) if total_requests else 0,
                            'avg_response_time': avg_response_time,
                            'on_time_responses': on_time_responses,
                            'on_time_rate': (on_time_responses / total_responded * 100) if total_responded else 0
                        },

                        # Fulfillment stats
                        'fulfillment_stats': {
                            'total_requests': total_requests,
                            'fulfilled_requests': total_fulfilled,
                            'fulfillment_rate': (total_fulfilled / total_requests * 100) if total_requests else 0
                        },

                        # Purchase type stats
                        'purchase_type_stats': {
                            'part': {
                                'total': purchase_stats['part']['total'],
                                'successful': purchase_stats['part']['success'],
                                'success_rate': (purchase_stats['part']['success'] / purchase_stats['part']['total'] * 100) 
                                    if purchase_stats['part']['total'] else 0
                            },
                            'tool': {
                                'total': purchase_stats['tool']['total'],
                                'successful': purchase_stats['tool']['success'],
                                'success_rate': (purchase_stats['tool']['success'] / purchase_stats['tool']['total'] * 100)
                                    if purchase_stats['tool']['total'] else 0
                            }
                        },
                        
                        # Add completeness
                        'completeness_stats': [{
                            'type': stat['purchase_type'],
                            'avg_completeness': stat['actual_completeness']
                        } for stat in completeness_stats],
                        
                        'completion_rate': (completed_purchases / total_purchases * 100) if total_purchases else 0,
                        'average_duration': avg_duration,
                        'average_duration_display': self._format_duration(avg_duration)
                    },
                    'partman_performance': [{
                        'partman_id': stat['partman_id'][0],
                        'partman_name': stat['partman_id'][1],
                        'avg_duration': stat['duration'],
                        'avg_duration_display': self._format_duration(stat['duration'])
                    } for stat in partman_stats if stat['partman_id']]
                }
            }

        except Exception as e:
            _logger.error(f"Error in get_statistics: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _format_duration(self, duration_hours):
        """Format duration from hours to readable string"""
        if not duration_hours:
            return "0j 0m"
        hours = int(duration_hours)
        minutes = int((duration_hours - hours) * 60)
        return f"{hours}j {minutes}m"

    @http.route('/web/sale-order/recompute', type='json', auth='user', methods=['POST'])
    def recompute_lead_time(self, **kw):
        """Recompute lead time for sale orders with optimization"""
        try:
            all_orders = kw.get('all_orders')
            order_ids = kw.get('order_ids', [])
            batch_size = kw.get('batch_size', 50)  # Process 50 orders per batch
            
            SaleOrder = request.env['sale.order']
            recomputed = 0
            errors = 0
            
            # Get orders to process
            base_domain = [
                ('state', '=', 'sale'),
                ('controller_mulai_servis', '!=', False),
                ('controller_selesai', '!=', False)
            ]
            
            if all_orders:
                total_orders = SaleOrder.search_count(base_domain)
                total_batches = (total_orders + batch_size - 1) // batch_size
                
                for batch_num in range(total_batches):
                    offset = batch_num * batch_size
                    batch_orders = SaleOrder.search(base_domain, limit=batch_size, offset=offset)
                    
                    self._process_batch(batch_orders, recomputed, errors)
                    request.env.cr.commit()  # Commit after each batch
                    
            elif order_ids:
                orders = SaleOrder.browse(order_ids)
                self._process_batch(orders, recomputed, errors)
            else:
                return {'status': 'error', 'message': 'Either order_ids or all_orders parameter is required'}

            return {
                'status': 'success',
                'data': {
                    'total_processed': recomputed + errors,
                    'recomputed': recomputed,
                    'errors': errors
                }
            }

        except Exception as e:
            _logger.error(f"Error in recompute_lead_time: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _process_batch(self, orders, recomputed, errors):
        """Process a batch of orders"""
        # Cache timezone
        tz = pytz.timezone('Asia/Jakarta')
        
        # Pre-fetch all required attendances for batch
        employee_ids = orders.mapped('car_mechanic_id_new.employee_id').ids
        min_date = min(orders.mapped('controller_mulai_servis'))
        max_date = max(orders.mapped('controller_selesai'))
        
        # Get all attendances in one query
        attendance_domain = [
            ('employee_id', 'in', employee_ids),
            ('check_in', '<=', max_date),
            ('check_out', '>=', min_date),
            ('check_out', '!=', False)
        ]
        all_attendances = request.env['hr.attendance'].sudo().search(attendance_domain)
        
        # Group attendances by employee
        attendance_by_employee = {}
        for att in all_attendances:
            if att.employee_id.id not in attendance_by_employee:
                attendance_by_employee[att.employee_id.id] = []
            attendance_by_employee[att.employee_id.id].append(att)

        # Process each order
        for order in orders:
            try:
                # Invalidate cache
                order.invalidate_cache(['lead_time_servis', 'total_lead_time_servis'])
                
                # Store old values
                old_values = {
                    'total': order.total_lead_time_servis,
                    'net': order.lead_time_servis
                }
                
                # Recompute lead time
                order._compute_lead_time_servis()
                
                # Only process productive hours if mechanic assigned
                if order.car_mechanic_id_new:
                    productive_hours = {}
                    for mechanic in order.car_mechanic_id_new:
                        if not mechanic.employee_id:
                            continue
                            
                        # Get pre-fetched attendances for this employee
                        emp_attendances = attendance_by_employee.get(mechanic.employee_id.id, [])
                        if not emp_attendances:
                            continue
                            
                        hours = self._calculate_mechanic_hours(
                            order, mechanic, emp_attendances, tz
                        )
                        if hours > 0:
                            productive_hours[mechanic.id] = hours

                    # Log results if there are changes
                    if old_values['total'] != order.total_lead_time_servis or old_values['net'] != order.lead_time_servis:
                        mechanic_hours = [
                            f"{mechanic.name}: {hours:.2f} jam"
                            for mechanic_id, hours in productive_hours.items()
                            for mechanic in order.car_mechanic_id_new.filtered(lambda m: m.id == mechanic_id)
                        ]

                        msg = f"""
                            <p><strong>Lead Time Re-calculation Result</strong></p>
                            <ul>
                                <li>Total Lead Time: {old_values['total']:.2f} → {order.total_lead_time_servis:.2f} jam</li>
                                <li>Lead Time Bersih: {old_values['net']:.2f} → {order.lead_time_servis:.2f} jam</li>
                                {'<li>Productive Hours:</li><ul>' + ''.join(f'<li>{mh}</li>' for mh in mechanic_hours) + '</ul>' if mechanic_hours else ''}
                            </ul>
                        """
                        order.message_post(body=msg, message_type='notification')

                recomputed += 1
                
            except Exception as e:
                _logger.error(f"Error processing order {order.name}: {str(e)}")
                errors += 1

    def _calculate_mechanic_hours(self, order, mechanic, attendances, tz):
        """Calculate productive hours for a mechanic (optimized)"""
        total_hours = 0
        work_periods = []
        
        # First pass: collect all valid work periods
        for att in attendances:
            start = max(order.controller_mulai_servis, att.check_in)
            end = min(order.controller_selesai, att.check_out)
            if end > start:
                work_periods.append((start, end))
        
        # Second pass: merge overlapping periods and calculate hours
        if work_periods:
            work_periods.sort()
            merged = [work_periods[0]]
            
            for current in work_periods[1:]:
                previous = merged[-1]
                if current[0] <= previous[1]:
                    merged[-1] = (previous[0], max(previous[1], current[1]))
                else:
                    merged.append(current)
            
            # Calculate hours for merged periods
            for start, end in merged:
                start_local = pytz.utc.localize(start).astimezone(tz)
                end_local = pytz.utc.localize(end).astimezone(tz)
                
                work_hours = order.calculate_effective_hours(start, end)
                total_hours += work_hours
        
        return total_hours
