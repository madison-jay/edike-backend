from flask import request, jsonify, g, current_app
from api.v1.auth import login_required, role_required
from api.v1.services.hr.attendance_biometrics_service import BiometricService
from api.v1.views import app_views
import traceback
from datetime import datetime


def generate_biometric_employee_code(employee_id):
    """Generate a unique biometric employee code based on employee ID"""
    today = datetime.now()
    d = today.strftime("%d%m%y")
    return f"EMP{str(employee_id).split('-')[0]}{d}"

# create biometric employee
@app_views.route('hr/biometrics/employees/<uuid:employee_id>', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def create_biometric_employee(employee_id):
    """Create a new employee in the biometric system"""
    try:
        existing_employee = g.supabase_user_client.from_('employees').select('biotime_id, first_name, last_name').eq('id', str(employee_id)).execute()
        if existing_employee.data and existing_employee.data[0]['biotime_id']:
            return jsonify({"error": "Employee already has a biometric ID"}), 400
    
        emp_code = generate_biometric_employee_code(employee_id)
        biometric_service = BiometricService()
        first_name = existing_employee.data[0]['first_name']
        last_name = existing_employee.data[0]['last_name']
        
        created_employee = biometric_service.create_biometric_employee(emp_code, first_name, last_name)
        employee = g.supabase_user_client.from_('employees').update({
            'biotime_id': emp_code
        }).eq('id', str(employee_id)).execute()

        if not employee.data:
            return jsonify({"error": "Failed to update employee with biometric ID"}), 500
        return jsonify(created_employee), 201
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# delete biometric employee
@app_views.route('hr/biometrics/employees/<uuid:employee_id>', methods=['DELETE'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def delete_biometric_employee(employee_id):
    """Delete an employee from the biometric system"""
    try:
        # Fetch employee to get biotime_id
        emp_response = g.supabase_user_client.from_('employees').select('biotime_id').eq('id', str(employee_id)).execute()
        if not emp_response.data or not emp_response.data[0]['biotime_id']:
            return jsonify({"error": "Employee biometric ID not found"}), 404
        
        biotime_id = emp_response.data[0]['biotime_id']
        biometric_service = BiometricService()
        delete_response = biometric_service.delete_biometric_employee(biotime_id)

        # Optionally, remove biotime_id from employee record
        g.supabase_user_client.from_('employees').update({
            'biotime_id': None
        }).eq('id', str(employee_id)).execute()

        return jsonify(delete_response), 200
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# sync attendance transactions from biometric device
@app_views.route('hr/biometrics/sync-attendance', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def sync_attendance_transactions():
    """Sync attendance transactions from biometric device"""
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        biometric_service = BiometricService()
        store_response = biometric_service.sync_attendance(start_date=start_date, end_date=end_date)
        return jsonify(store_response), 200
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

# fetch attendance transactions from supabase
@app_views.route('hr/biometrics/attendance-transactions', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager'])
def fetch_attendance_transactions():
    """Fetch attendance transactions from Supabase"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        query = g.supabase_user_client.from_('attendance_transactions').select('employee:employee_id(first_name, last_name, id, email, avatar_url), date, check_in, check_out, status')
        if start_date:
            query = query.gte('date', start_date)
        if end_date:
            query = query.lte('date', end_date)
        
        response = query.execute()
        return jsonify(response.data), 200
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


#fetch per employee attendance transactions
@app_views.route('hr/biometrics/attendance-transactions/<uuid:employee_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager', 'user'])
def fetch_employee_attendance_transactions(employee_id):
    """Fetch attendance transactions for a specific employee from Supabase"""
    try:
        
        response = g.supabase_user_client.from_('attendance_transactions').select('*').eq('employee_id', str(employee_id)).execute()
        return jsonify(response.data), 200
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500