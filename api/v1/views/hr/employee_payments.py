from flask import g, current_app, jsonify, request
from api.v1.views import app_views
from api.v1.auth import login_required, role_required
from pydantic import ValidationError
from api.v1.services.hr.payroll_services import (
    get_employees_payment_data,
    generate_employee_payment,
    employee_payment_records
)
from datetime import datetime
from uuid import UUID
import traceback

def is_valid_uuid(uuid_string):
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False

@app_views.route('/employee_payments', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'manager' , 'user'])
def get_employee_payments():
    """Fetch all employee payments."""
    try:
        employee_payment_data = get_employees_payment_data("")
        if not employee_payment_data:
            return jsonify({"message": "No employee payments found"}), 204
        return jsonify(employee_payment_data), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching employee payments: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app_views.route('/employee_payments/<uuid:employee_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'user'])
def get_employee_payment(employee_id: str):
    """Fetch a specific employee's payment details."""
    print("employee id is", employee_id)
    
    try:
        employee_payment_data = get_employees_payment_data(employee_id)
        if not employee_payment_data:
            return jsonify({"message": "No payment found for this employee"}), 204
        return jsonify(employee_payment_data), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching employee payment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app_views.route('/employee_payments/<uuid:employee_id>', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def create_employee_payment(employee_id: str):
    """create payment for employees at any given month."""
    
    try:
        employee_check = g.supabase_user_client.from_('employees').select('id').eq('id', employee_id).is_('deleted_at', 'null').execute()
        if not employee_check.data:
            return jsonify({"error": "Employee Not found or Not Active"}), 204
        period = datetime.now().strftime('%Y-%m')

        created_by_response = g.supabase_user_client.from_('employees').select('id, next_due_date').eq('user_id', g.current_user).execute()
        if not created_by_response.data:
            return jsonify({"error": "Creator employee record not found"}), 404
        created_by = created_by_response.data[0]['id']
        next_due_date = created_by_response.data[0]['next_due_date']

        payment = generate_employee_payment(employee_id, period, created_by, next_due_date)
        return jsonify({
            "status": "success",
            "data": payment,
            "message": f"Payment generated for employee {employee_id} for {period}"
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error creating employee payment: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app_views.route('/employee_payments/all', methods=['POST'])
@login_required
@role_required(['super_admin', 'hr_manager'])
def create_bulk_employee_payments():
    """Create payments for all employees."""
    try:
        period = datetime.now().strftime('%Y-%m')
        created_by_response = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).execute()
        if not created_by_response.data:
            return jsonify({"error": "Creator employee record not found"}), 404
        created_by = created_by_response.data[0]['id']
        next_due_date = created_by_response.data[0]['next_due_date']

        

        payments = []

        employees_response = g.supabase_user_client.from_('employees').select('id').is_('deleted_at', 'null').execute()
        if not employees_response.data:
            return jsonify({"error": "No active employees found"}), 204
        for employee in employees_response.data:
            try:
                print(f"Generating payment for employee {employee} for period {period}")
                payment = generate_employee_payment(employee['id'], period, created_by, next_due_date)
                payments.append(payment)
            except Exception as e:
                current_app.logger.error(f"Error generating payment for employee {employee['id']}: {str(e)}")
                print(f"Error generating payment for employee {employee['id']}: {str(e)}")
        return jsonify({
            "status": "success",
            "data": payments,
            "message": f"Payments generated for {len(payments)} employees for {period}"
        }), 200

    except Exception as e:
        traceback.print_exc()
        print(f"Error creating bulk employee payments: {str(e)}")
        current_app.logger.error(f"Error creating bulk employee payments: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

#fetch user payroll
@app_views.route('/employee_payments/payroll/<uuid:employee_id>', methods=['GET'])
@login_required
@role_required(['super_admin', 'hr_manager', 'user', 'manager'])
def get_employee_payroll(employee_id: str):
    """Fetch payroll details for a specific employee."""
    try:
        print('here')
        # if not is_valid_uuid(employee_id):
        #     return jsonify({"error": "Invalid employee ID format"}), 400
        print('here now')
        payroll_data = employee_payment_records(employee_id)
        if not payroll_data:
            return jsonify([]), 204
        return jsonify(payroll_data), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching employee payroll: {str(e)}")
        return jsonify({"error": str(e)}), 500