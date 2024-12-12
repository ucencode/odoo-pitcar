# controllers/attendance_api.py
from odoo import http
from odoo.http import request
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import logging
import json
import math

_logger = logging.getLogger(__name__)

class AttendanceAPI(http.Controller):
    def _euclidean_distance(self, descriptor1, descriptor2):
        """Calculate Euclidean distance between two face descriptors"""
        try:
            if len(descriptor1) != len(descriptor2):
                return float('inf')
                
            sum_squares = 0
            for d1, d2 in zip(descriptor1, descriptor2):
                diff = d1 - d2
                sum_squares += diff * diff
                
            distance = math.sqrt(sum_squares)
            # Convert distance to similarity score (0 to 1)
            similarity = 1 / (1 + distance)
            return similarity
            
        except Exception as e:
            _logger.error(f"Error calculating face similarity: {str(e)}")
            return 0
        
    @http.route('/web/v2/attendance/verify-face', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def verify_face(self, **kw):
        """Verify face descriptor against registered face"""
        try:
            # Extract params from JSONRPC request
            params = kw.get('params', kw)
            face_descriptor = params.get('face_descriptor')
            
            if not face_descriptor:
                return {'status': 'error', 'message': 'Face descriptor is required'}

            # Get employee
            employee = request.env.user.employee_id
            if not employee:
                return {'status': 'error', 'message': 'Employee not found'}

            # Get stored face descriptor
            stored_descriptor = employee.face_descriptor
            if not stored_descriptor:
                return {'status': 'error', 'message': 'No registered face found'}

            # Verify face
            verification_result = self._verify_face(face_descriptor, stored_descriptor)
            
            return {
                'status': 'success',
                'data': {
                    'is_match': verification_result['is_match'],
                    'similarity': verification_result['similarity'],
                    'employee_name': employee.name if verification_result['is_match'] else None
                }
            }

        except Exception as e:
            _logger.error(f"Error in verify_face: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _verify_face(self, current_descriptor, stored_descriptor, threshold=0.4):
        """Verify face with custom threshold"""
        try:
            # Convert stored descriptor from string if needed
            if isinstance(stored_descriptor, str):
                stored_descriptor = json.loads(stored_descriptor)
                
            # Convert descriptors to list of floats
            current_descriptor = [float(x) for x in current_descriptor]
            stored_descriptor = [float(x) for x in stored_descriptor]
            
            # Calculate similarity
            similarity = self._euclidean_distance(current_descriptor, stored_descriptor)
            
            return {
                'is_match': similarity >= threshold,
                'similarity': similarity
            }
            
        except Exception as e:
            _logger.error(f"Face verification error: {str(e)}")
            return {
                'is_match': False,
                'similarity': 0
            }

    @http.route('/web/v2/attendance/check', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def check_attendance(self, **kw):
        try:
            # Extract params
            params = kw.get('params', kw)
            
            # Basic validation
            required_fields = {
                'action_type': params.get('action_type'),
                'face_descriptor': params.get('face_descriptor'),
                'face_image': params.get('face_image'),  # Tambahkan face_image
                'location': params.get('location', {})
            }

            missing_fields = [k for k, v in required_fields.items() if not v]
            if missing_fields:
                return {'status': 'error', 'message': f"Missing required fields: {', '.join(missing_fields)}"}

            # Get employee
            employee = request.env.user.employee_id
            if not employee:
                return {'status': 'error', 'message': 'Employee not found'}

            # Verify face
            verification_result = self._verify_face(
                params['face_descriptor'], 
                employee.face_descriptor
            )
            
            if not verification_result['is_match']:
                return {'status': 'error', 'message': 'Face verification failed'}

            # Set timezone and get current time
            tz = pytz.timezone('Asia/Jakarta')
            now = datetime.now(tz)
            now_utc = now.astimezone(pytz.UTC).replace(tzinfo=None)

            # Create/update attendance
            values = {
                'employee_id': employee.id,
                'face_descriptor': json.dumps(params['face_descriptor']),
                'face_image': params['face_image']  # Simpan gambar wajah
            }

            if params['action_type'] == 'check_in':
                values['check_in'] = now_utc
                attendance = request.env['hr.attendance'].sudo().create(values)
            else:  # check_out
                attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1)
                
                if not attendance:
                    return {'status': 'error', 'message': 'No active attendance found'}
                
                values['check_out'] = now_utc
                attendance.write(values)

            return {
                'status': 'success',
                'data': {
                    'attendance_id': attendance.id,
                    'employee': {
                        'id': employee.id,
                        'name': employee.name
                    },
                    'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
                    'type': params['action_type'],
                    'location': params['location']
                }
            }

        except Exception as e:
            _logger.error(f"Error in check_attendance: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/web/v2/attendance/validate-location', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def validate_location(self, **kw):
        """Validate if user's location is within allowed work locations"""
        try:
            location = kw.get('location', {})
            
            # Get employee from current user
            employee = request.env.user.employee_id
            if not employee:
                return {'status': 'error', 'message': 'Employee not found'}

            # Check if employee has valid work locations
            work_locations = request.env['pitcar.work.location'].sudo().search([])
            
            if not work_locations:
                # Jika tidak ada work location yang didefinisikan, anggap valid
                return {
                    'status': 'success',
                    'data': {
                        'isValid': True,
                        'allowed_locations': []
                    }
                }

            # Validate location
            is_valid = False
            for loc in work_locations:
                distance = loc.calculate_distance(
                    location.get('latitude'),
                    location.get('longitude')
                )
                if distance <= loc.radius:
                    is_valid = True
                    break

            return {
                'status': 'success',
                'data': {
                    'isValid': is_valid,
                    'allowed_locations': [{
                        'name': loc.name,
                        'latitude': loc.latitude,
                        'longitude': loc.longitude,
                        'radius': loc.radius
                    } for loc in work_locations]
                }
            }

        except Exception as e:
            _logger.error(f"Error in validate_location: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/web/v2/attendance/register-face', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def register_face(self, **kw):
        """Register face descriptor and image for employee"""
        try:
            # Ambil params dari kw langsung seperti endpoint lain
            face_descriptor = kw.get('face_descriptor')
            face_image = kw.get('face_image')

            # Validasi face descriptor
            if not face_descriptor:
                return {'status': 'error', 'message': 'Face descriptor is required'}

            # Get employee
            employee = request.env.user.employee_id
            if not employee:
                return {'status': 'error', 'message': 'Employee not found'}

            # Save to employee record
            values = {
                'face_descriptor': json.dumps(face_descriptor),
                'face_image': face_image if face_image else False
            }

            employee.write(values)

            return {
                'status': 'success',
                'message': 'Face registered successfully',
                'data': {
                    'employee_id': employee.id,
                    'name': employee.name
                }
            }

        except Exception as e:
            _logger.error(f"Error in register_face: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/web/v2/attendance/status', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def get_attendance_status(self, **kw):
        try:
            # Extract params
            params = kw.get('params', kw)
            face_descriptor = params.get('face_descriptor')
            
            employee = request.env.user.employee_id
            if not employee:
                return {'status': 'error', 'message': 'Employee not found'}

            # Set timezone to Asia/Jakarta
            jakarta_tz = pytz.timezone('Asia/Jakarta')
            
            # Get current datetime in Jakarta timezone
            now = datetime.now(jakarta_tz)
            today = now.date()
            
            # Get start and end of today in UTC (for database queries)
            today_start_utc = jakarta_tz.localize(datetime.combine(today, time.min)).astimezone(pytz.UTC)
            today_end_utc = jakarta_tz.localize(datetime.combine(today, time.max)).astimezone(pytz.UTC)

            # Get today's attendance using UTC times for query
            today_attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', today_start_utc.strftime('%Y-%m-%d %H:%M:%S')),
                ('check_in', '<', today_end_utc.strftime('%Y-%m-%d %H:%M:%S'))
            ], limit=1, order='check_in desc')

            # Get last 2 attendances (excluding today)
            last_attendances = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_in', '<', today_start_utc.strftime('%Y-%m-%d %H:%M:%S'))
            ], limit=2, order='check_in desc')

            # Get current month summary
            first_day = today.replace(day=1)
            last_day = (first_day + relativedelta(months=1, days=-1))
            
            # Convert month boundaries to UTC for database query
            month_start_utc = jakarta_tz.localize(datetime.combine(first_day, time.min)).astimezone(pytz.UTC)
            month_end_utc = jakarta_tz.localize(datetime.combine(last_day, time.max)).astimezone(pytz.UTC)
            
            month_attendances = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', month_start_utc.strftime('%Y-%m-%d %H:%M:%S')),
                ('check_in', '<=', month_end_utc.strftime('%Y-%m-%d %H:%M:%S'))
            ])

            # Calculate monthly statistics
            # Use set to count unique dates in Jakarta timezone
            present_days = len(set(att.check_in.astimezone(jakarta_tz).date() for att in month_attendances))
            total_working_days = 26  # Standard working days per month
            
            # Standard work start time in Jakarta (8 AM)
            work_start_time = time(8, 0)
            
            # Count late attendances (check-in after 8 AM Jakarta time)
            late_attendances = []
            total_late_minutes = 0
            
            for att in month_attendances:
                check_in_jkt = att.check_in.astimezone(jakarta_tz)
                if check_in_jkt.time() > work_start_time:
                    late_attendances.append(att)
                    # Calculate late duration
                    scheduled_start = jakarta_tz.localize(
                        datetime.combine(check_in_jkt.date(), work_start_time)
                    )
                    late_minutes = (check_in_jkt - scheduled_start).total_seconds() / 60
                    total_late_minutes += late_minutes

            # Face verification if descriptor provided
            face_verification = None
            if face_descriptor and employee.face_descriptor:
                face_verification = self._verify_face(face_descriptor, employee.face_descriptor)

            # Check if currently checked in
            current_attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], limit=1)

            def format_attendance(attendance):
                if not attendance:
                    return None
                    
                check_in_jkt = attendance.check_in.astimezone(jakarta_tz)
                is_late = check_in_jkt.time() > work_start_time
                late_duration = 0
                
                if is_late:
                    scheduled_start = jakarta_tz.localize(
                        datetime.combine(check_in_jkt.date(), work_start_time)
                    )
                    late_duration = (check_in_jkt - scheduled_start).total_seconds() / 60

                working_hours = 0
                if attendance.check_out:
                    check_out_jkt = attendance.check_out.astimezone(jakarta_tz)
                    working_hours = (check_out_jkt - check_in_jkt).total_seconds() / 3600

                return {
                    'id': attendance.id,
                    'date': check_in_jkt.date().isoformat(),
                    'status': 'present',
                    'check_in': check_in_jkt.isoformat(),
                    'check_out': attendance.check_out.astimezone(jakarta_tz).isoformat() if attendance.check_out else None,
                    'is_late': is_late,
                    'late_duration': int(late_duration),
                    'working_hours': round(working_hours, 2)
                }

            # Calculate total and average working hours
            total_hours = sum(
                (att.check_out - att.check_in).total_seconds() / 3600 
                for att in month_attendances if att.check_out
            )
            avg_hours = round(total_hours / present_days, 2) if present_days > 0 else 0

            return {
                'status': 'success',
                'data': {
                    'is_checked_in': bool(current_attendance),
                    'has_face_registered': bool(employee.face_descriptor),
                    'face_verification': face_verification,
                    'today_attendance': format_attendance(today_attendance) if today_attendance else None,
                    'last_attendances': [format_attendance(att) for att in last_attendances if att],
                    'monthly_summary': {
                        'month': now.strftime('%B'),
                        'year': now.year,
                        'total_working_days': total_working_days,
                        'attendance_summary': {
                            'present': present_days,
                            'absent': total_working_days - present_days,
                            'leave': 0  # Optional: bisa ditambahkan jika ada sistem cuti
                        },
                        'late_summary': {
                            'total_late_days': len(late_attendances),
                            'total_late_hours': round(total_late_minutes / 60, 1),
                            'average_late_duration': round(total_late_minutes / len(late_attendances) if late_attendances else 0)
                        },
                        'working_hours_summary': {
                            'total_hours': round(total_hours, 2),
                            'average_hours': avg_hours
                        }
                    },
                    'employee': {
                        'id': employee.id,
                        'name': employee.name
                    }
                }
            }

        except Exception as e:
            _logger.error(f"Error in get_attendance_status: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/web/v2/attendance/dashboard', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def get_attendance_dashboard(self, **kw):
        """Get attendance dashboard data with metrics"""
        try:
            # Get date range parameters
            date_range = kw.get('date_range', 'today')
            start_date = kw.get('start_date')
            end_date = kw.get('end_date')
            
            # Set timezone
            tz = pytz.timezone('Asia/Jakarta')
            now = datetime.now(tz)
            
            # Calculate date range similar to service advisor
            if start_date and end_date:
                try:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    end = datetime.strptime(end_date, '%Y-%m-%d')
                    start = tz.localize(start.replace(hour=0, minute=0, second=0))
                    end = tz.localize(end.replace(hour=23, minute=59, second=59))
                except (ValueError, TypeError):
                    return {'status': 'error', 'message': 'Invalid date format'}
            else:
                # Date range logic similar to service advisor
                if date_range == 'today':
                    start = now.replace(hour=0, minute=0, second=0)
                    end = now
                elif date_range == 'yesterday':
                    yesterday = now - timedelta(days=1)
                    start = yesterday.replace(hour=0, minute=0, second=0)
                    end = yesterday.replace(hour=23, minute=59, second=59)
                elif date_range == 'this_week':
                    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
                    end = now
                elif date_range == 'this_month':
                    start = now.replace(day=1, hour=0, minute=0, second=0)
                    end = now
                else:
                    start = now.replace(hour=0, minute=0, second=0)
                    end = now

            # Convert to UTC for database queries
            start_utc = start.astimezone(pytz.UTC)
            end_utc = end.astimezone(pytz.UTC)

            # Get all mechanics
            mechanics = request.env['pitcar.mechanic.new'].sudo().search([])
            mechanic_dict = {m.employee_id.id: m for m in mechanics}

            # Get all attendance records
            domain = [
                ('check_in', '>=', start_utc.strftime('%Y-%m-%d %H:%M:%S')),
                ('check_in', '<=', end_utc.strftime('%Y-%m-%d %H:%M:%S'))
            ]
            
            all_attendances = request.env['hr.attendance'].sudo().search(domain)

            # Calculate metrics
            mechanic_data = {}
            total_hours = 0
            total_attendance = 0
            total_late = 0
            on_time_attendance = 0

            for attendance in all_attendances:
                employee = attendance.employee_id
                mechanic = mechanic_dict.get(employee.id)
                
                if not mechanic:
                    continue

                if mechanic.id not in mechanic_data:
                    mechanic_data[mechanic.id] = {
                        'id': mechanic.id,
                        'name': mechanic.name,
                        'position': mechanic.position_id.name,
                        'leader': mechanic.leader_id.name if mechanic.leader_id else None,
                        'total_hours': 0,
                        'attendance_count': 0,
                        'late_count': 0,
                        'on_time_count': 0,
                        'work_hours_target': mechanic.work_hours_target
                    }

                data = mechanic_data[mechanic.id]
                
                # Calculate working hours
                worked_hours = attendance.worked_hours or 0
                data['total_hours'] += worked_hours
                data['attendance_count'] += 1

                # Calculate late/on-time (example: late if check-in after 8 AM)
                check_in_time = pytz.utc.localize(attendance.check_in).astimezone(tz)
                target_time = check_in_time.replace(hour=8, minute=0, second=0)
                
                if check_in_time > target_time:
                    data['late_count'] += 1
                    total_late += 1
                else:
                    data['on_time_count'] += 1
                    on_time_attendance += 1

                total_hours += worked_hours
                total_attendance += 1

            # Format response similar to service advisor
            active_mechanics = []
            for data in mechanic_data.values():
                metrics = {
                    'attendance': {
                        'total_hours': data['total_hours'],
                        'target_hours': data['work_hours_target'] * data['attendance_count'],
                        'achievement': (data['total_hours'] / (data['work_hours_target'] * data['attendance_count']) * 100) 
                                    if data['attendance_count'] else 0
                    },
                    'punctuality': {
                        'total_attendance': data['attendance_count'],
                        'on_time': data['on_time_count'],
                        'late': data['late_count'],
                        'on_time_rate': (data['on_time_count'] / data['attendance_count'] * 100) 
                                    if data['attendance_count'] else 0
                    }
                }

                active_mechanics.append({
                    'id': data['id'],
                    'name': data['name'],
                    'position': data['position'],
                    'leader': data['leader'],
                    'metrics': metrics
                })

            # Calculate overview metrics
            overview = {
                'total_hours': total_hours,
                'total_attendance': total_attendance,
                'punctuality': {
                    'on_time': on_time_attendance,
                    'late': total_late,
                    'on_time_rate': (on_time_attendance / total_attendance * 100) if total_attendance else 0
                }
            }

            return {
                'status': 'success',
                'data': {
                    'date_range': {
                        'type': date_range,
                        'start': start.strftime('%Y-%m-%d'),
                        'end': end.strftime('%Y-%m-%d')
                    },
                    'overview': overview,
                    'mechanics': active_mechanics
                }
            }

        except Exception as e:
            _logger.error(f"Error in get_attendance_dashboard: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _verify_location(self, mechanic, location, device_info):
        """Helper method to verify location"""
        try:
            if device_info.get('isMockLocationOn'):
                return False

            if not mechanic or not mechanic.work_location_ids:
                return True

            lat = location.get('latitude')
            lon = location.get('longitude')

            for work_location in mechanic.work_location_ids:
                distance = work_location.calculate_distance(lat, lon)
                if distance <= work_location.radius:
                    return True

            return False
        except Exception as e:
            _logger.error(f"Location verification error: {str(e)}")
            return False

    @http.route('/web/v2/attendance/dashboard', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def get_attendance_dashboard(self, **kw):
        """Get attendance dashboard data with metrics"""
        try:
            # Get date range parameters
            date_range = kw.get('date_range', 'today')
            start_date = kw.get('start_date')
            end_date = kw.get('end_date')
            
            # Set timezone
            tz = pytz.timezone('Asia/Jakarta')
            now = datetime.now(tz)
            
            # Calculate date range similar to service advisor
            if start_date and end_date:
                try:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    end = datetime.strptime(end_date, '%Y-%m-%d')
                    start = tz.localize(start.replace(hour=0, minute=0, second=0))
                    end = tz.localize(end.replace(hour=23, minute=59, second=59))
                except (ValueError, TypeError):
                    return {'status': 'error', 'message': 'Invalid date format'}
            else:
                # Date range logic similar to service advisor
                if date_range == 'today':
                    start = now.replace(hour=0, minute=0, second=0)
                    end = now
                elif date_range == 'yesterday':
                    yesterday = now - timedelta(days=1)
                    start = yesterday.replace(hour=0, minute=0, second=0)
                    end = yesterday.replace(hour=23, minute=59, second=59)
                elif date_range == 'this_week':
                    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
                    end = now
                elif date_range == 'this_month':
                    start = now.replace(day=1, hour=0, minute=0, second=0)
                    end = now
                else:
                    start = now.replace(hour=0, minute=0, second=0)
                    end = now

            # Convert to UTC for database queries
            start_utc = start.astimezone(pytz.UTC)
            end_utc = end.astimezone(pytz.UTC)

            # Get all mechanics
            mechanics = request.env['pitcar.mechanic.new'].sudo().search([])
            mechanic_dict = {m.employee_id.id: m for m in mechanics}

            # Get all attendance records
            domain = [
                ('check_in', '>=', start_utc.strftime('%Y-%m-%d %H:%M:%S')),
                ('check_in', '<=', end_utc.strftime('%Y-%m-%d %H:%M:%S'))
            ]
            
            all_attendances = request.env['hr.attendance'].sudo().search(domain)

            # Calculate metrics
            mechanic_data = {}
            total_hours = 0
            total_attendance = 0
            total_late = 0
            on_time_attendance = 0

            for attendance in all_attendances:
                employee = attendance.employee_id
                mechanic = mechanic_dict.get(employee.id)
                
                if not mechanic:
                    continue

                if mechanic.id not in mechanic_data:
                    mechanic_data[mechanic.id] = {
                        'id': mechanic.id,
                        'name': mechanic.name,
                        'position': mechanic.position_id.name,
                        'leader': mechanic.leader_id.name if mechanic.leader_id else None,
                        'total_hours': 0,
                        'attendance_count': 0,
                        'late_count': 0,
                        'on_time_count': 0,
                        'work_hours_target': mechanic.work_hours_target
                    }

                data = mechanic_data[mechanic.id]
                
                # Calculate working hours
                worked_hours = attendance.worked_hours or 0
                data['total_hours'] += worked_hours
                data['attendance_count'] += 1

                # Calculate late/on-time (example: late if check-in after 8 AM)
                check_in_time = pytz.utc.localize(attendance.check_in).astimezone(tz)
                target_time = check_in_time.replace(hour=8, minute=0, second=0)
                
                if check_in_time > target_time:
                    data['late_count'] += 1
                    total_late += 1
                else:
                    data['on_time_count'] += 1
                    on_time_attendance += 1

                total_hours += worked_hours
                total_attendance += 1

            # Format response similar to service advisor
            active_mechanics = []
            for data in mechanic_data.values():
                metrics = {
                    'attendance': {
                        'total_hours': data['total_hours'],
                        'target_hours': data['work_hours_target'] * data['attendance_count'],
                        'achievement': (data['total_hours'] / (data['work_hours_target'] * data['attendance_count']) * 100) 
                                    if data['attendance_count'] else 0
                    },
                    'punctuality': {
                        'total_attendance': data['attendance_count'],
                        'on_time': data['on_time_count'],
                        'late': data['late_count'],
                        'on_time_rate': (data['on_time_count'] / data['attendance_count'] * 100) 
                                    if data['attendance_count'] else 0
                    }
                }

                active_mechanics.append({
                    'id': data['id'],
                    'name': data['name'],
                    'position': data['position'],
                    'leader': data['leader'],
                    'metrics': metrics
                })

            # Calculate overview metrics
            overview = {
                'total_hours': total_hours,
                'total_attendance': total_attendance,
                'punctuality': {
                    'on_time': on_time_attendance,
                    'late': total_late,
                    'on_time_rate': (on_time_attendance / total_attendance * 100) if total_attendance else 0
                }
            }

            return {
                'status': 'success',
                'data': {
                    'date_range': {
                        'type': date_range,
                        'start': start.strftime('%Y-%m-%d'),
                        'end': end.strftime('%Y-%m-%d')
                    },
                    'overview': overview,
                    'mechanics': active_mechanics
                }
            }

        except Exception as e:
            _logger.error(f"Error in get_attendance_dashboard: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _verify_location(self, mechanic, location, device_info):
        """Helper method to verify location"""
        try:
            if device_info.get('isMockLocationOn'):
                return False

            if not mechanic or not mechanic.work_location_ids:
                return True

            lat = location.get('latitude')
            lon = location.get('longitude')

            for work_location in mechanic.work_location_ids:
                distance = work_location.calculate_distance(lat, lon)
                if distance <= work_location.radius:
                    return True

            return False
        except Exception as e:
            _logger.error(f"Location verification error: {str(e)}")
            return False

    # Tambahkan endpoint-endpoint berikut ke class AttendanceAPI
    @http.route('/web/v2/work-locations', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def get_work_locations(self, **kw):
        """Get all work locations"""
        try:
            locations = request.env['pitcar.work.location'].sudo().search([])
            return {
                'status': 'success',
                'data': [{
                    'id': loc.id,
                    'name': loc.name,
                    'latitude': loc.latitude,
                    'longitude': loc.longitude,
                    'radius': loc.radius,
                    'address': loc.address,
                    'active': loc.active
                } for loc in locations]
            }
        except Exception as e:
            _logger.error(f"Error in get_work_locations: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/web/v2/work-locations/create', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def create_work_location(self, **kw):
        """Create new work location"""
        try:
            # Extract params
            params = kw.get('params', {})
            required_fields = ['name', 'latitude', 'longitude', 'radius']
            
            # Validate required fields
            missing_fields = [field for field in required_fields if not params.get(field)]
            if missing_fields:
                return {
                    'status': 'error',
                    'message': f"Missing required fields: {', '.join(missing_fields)}"
                }
                
            # Create work location
            values = {
                'name': params['name'],
                'latitude': float(params['latitude']),
                'longitude': float(params['longitude']),
                'radius': int(params['radius']),
                'address': params.get('address', ''),
                'active': params.get('active', True)
            }
            
            location = request.env['pitcar.work.location'].sudo().create(values)
            
            return {
                'status': 'success',
                'data': {
                    'id': location.id,
                    'name': location.name,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'radius': location.radius,
                    'address': location.address,
                    'active': location.active
                }
            }
        except Exception as e:
            _logger.error(f"Error in create_work_location: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/web/v2/work-locations/update/<int:location_id>', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def update_work_location(self, location_id, **kw):
        """Update existing work location"""
        try:
            # Check if location exists
            location = request.env['pitcar.work.location'].sudo().browse(location_id)
            if not location.exists():
                return {'status': 'error', 'message': 'Location not found'}
                
            # Extract params
            params = kw.get('params', {})
            
            # Update values if provided
            values = {}
            if 'name' in params:
                values['name'] = params['name']
            if 'latitude' in params:
                values['latitude'] = float(params['latitude'])
            if 'longitude' in params:
                values['longitude'] = float(params['longitude'])
            if 'radius' in params:
                values['radius'] = int(params['radius'])
            if 'address' in params:
                values['address'] = params['address']
            if 'active' in params:
                values['active'] = bool(params['active'])
                
            location.write(values)
            
            return {
                'status': 'success',
                'data': {
                    'id': location.id,
                    'name': location.name,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'radius': location.radius,
                    'address': location.address,
                    'active': location.active
                }
            }
        except Exception as e:
            _logger.error(f"Error in update_work_location: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/web/v2/work-locations/delete/<int:location_id>', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def delete_work_location(self, location_id, **kw):
        """Delete work location"""
        try:
            location = request.env['pitcar.work.location'].sudo().browse(location_id)
            if not location.exists():
                return {'status': 'error', 'message': 'Location not found'}
                
            location.unlink()
            
            return {
                'status': 'success',
                'message': 'Location deleted successfully'
            }
        except Exception as e:
            _logger.error(f"Error in delete_work_location: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/web/v2/work-locations/<int:location_id>', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def get_work_location(self, location_id, **kw):
        """Get single work location by ID"""
        try:
            location = request.env['pitcar.work.location'].sudo().browse(location_id)
            if not location.exists():
                return {'status': 'error', 'message': 'Location not found'}
                
            return {
                'status': 'success',
                'data': {
                    'id': location.id,
                    'name': location.name,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'radius': location.radius,
                    'address': location.address,
                    'active': location.active
                }
            }
        except Exception as e:
            _logger.error(f"Error in get_work_location: {str(e)}")
            return {'status': 'error', 'message': str(e)}