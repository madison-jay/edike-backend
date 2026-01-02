from flask import g, current_app
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID
from dateutil.relativedelta import relativedelta
import traceback



# Helper function for UUID validation
def is_valid_uuid(uuid_string: str) -> bool:
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False

# Pydantic Schemas
class DeductionCreateSchema(BaseModel):
    employee_id: str
    default_charge_id: str
    pardoned_fee: float = Field(0, ge=0)
    created_by: str = None
    status: Literal['pending', 'paid'] = 'pending'
    reason: Optional[str] = None
    instances: int = Field(1, ge=1)  # Number of instances for the deduction
    payment_history_id: Optional[str] = None  # Nullable, filled after payslip generation



class DeductionUpdateSchema(BaseModel):
    pardoned_fee: Optional[float] = Field(None, ge=0)
    status: Optional[Literal['pending', 'paid']] = None
    reason: Optional[str] = None
    instances: Optional[int] = Field(None, ge=1)  # Number of instances for the deduction
    payment_history_id: Optional[str] = None  # Nullable, filled after payslip generation

    class Config:
        extra = 'forbid'
 

class DefaultChargeCreateSchema(BaseModel):
    charge_name: str = Field(..., max_length=100)
    penalty_fee: float = Field(..., ge=0)
    description: Optional[str] = None
    created_by: Optional[str] = None  # Filled by API

   

class DefaultChargeUpdateSchema(BaseModel):
    charge_name: Optional[str] = Field(None, max_length=100)
    penalty_fee: Optional[float] = Field(None, ge=0)
    description: Optional[str] = None


class SalaryComponentCreateSchema(BaseModel):
    employee_id: str
    base_salary: float = Field(..., ge=0)
    bonus: Optional[float] = Field(0, ge=0)
    incentives: Optional[float] = Field(0, ge=0)
    start_date: str
    end_date: Optional[str] = None
    created_by: Optional[str] = None  # Filled by API


class SalaryComponentUpdateSchema(BaseModel):
    base_salary: Optional[float] = Field(None, ge=0)
    bonus: Optional[float] = Field(None, ge=0)
    incentives: Optional[float] = Field(None, ge=0)
    end_date: Optional[str] = None

 

class PaymentHistoryCreateSchema(BaseModel):
    employee_id: str
    payment_date: str
    month_year: str = Field(..., pattern=r'^\d{4}-\d{2}$')
    created_by: Optional[str] = None  # Filled by API


 
class PaymentHistoryUpdateSchema(BaseModel):
    payment_date: Optional[str] = None
    transaction_id: Optional[str] = None
    status: Optional[Literal['pending', 'completed']] = None  # If status column is added


def get_employees_payment_data(employee_id: str):
    """Fetch all employees' payment data."""
    try:
        deductions_details = []
        salary_details = []
        employee_details = []
        employees_response = None

        if employee_id:
            employees_response = g.supabase_user_client.table("employees").select("id, first_name, last_name, email, avatar_url, next_due_date, department:department_id(id,name)").eq("id", employee_id).neq('employment_status', 'terminated').execute()
        else:
            employees_response = g.supabase_user_client.table("employees").select("id, first_name, last_name, email, avatar_url, next_due_date, department:department_id(id,name)").neq('employment_status', 'terminated').execute()
        if employees_response.data:
            employee_details = employees_response.data

        deduction_response = g.supabase_user_client.table('unpaid_deductions_by_employee').select("*").execute()
        if deduction_response.data:
            deductions_details = deduction_response.data

        salary_response = g.supabase_user_client.table('salary_components').select("id, employee_id, base_salary, bonus, incentives").is_("end_date", "null").execute()
        if salary_response.data:
            salary_details = salary_response.data
        
        #combine deductions and salary details
        result = []
        deductions_dict = {d["employee_id"]: d for d in deductions_details}
        salary_dict = {s["employee_id"]: s for s in salary_details}

        for employee in employee_details:
           employee_id = employee['id']
           employee_data = {
               "month-year"
               "employee_details": {
                     "id": employee['id'],
                     "first_name": employee['first_name'],
                     "last_name": employee['last_name'],
                     "department": employee['department']['name'] if employee['department'] else None,
                     "email": employee['email'],
                     "avatar_url": employee['avatar_url'],
                     "next_due_date": employee['next_due_date']
               },
               "deductions": deductions_dict.get(employee_id, {
                   "total_deductions": 0,
                   "total_instances": 0,
                   "total_pardoned_fee": 0,
                   "deduction_details": []
               }),
               "salary": salary_dict.get(employee_id, {
                   "base_salary": 0,
                   "bonus": 0,
                   "incentives": 0
               })
           }
           result.append(employee_data)
        return result


    except Exception as e:
        traceback.print_exc()
        current_app.logger.error(f"Error fetching payment data: {str(e)}")
        raise e

def generate_employee_payment(employee_id: str, period: str, created_by: str, next_due_date: Optional[date] = None) -> dict:
    """
    Generate all employee payments for the current month.
    Returns :
        - A list of payment history IDs generated for the employee.
    """
    payment_response = None
    deduction_ids = []
    total_deductions = 0.0
    try:
        existing_payments = g.supabase_user_client.from_('payment_history').select('id, employee_id, payment_date, month_year, gross_salary, total_deductions, net_salary').eq("employee_id", employee_id).eq("month_year", period).execute()
        if existing_payments.data:
            return existing_payments.data[0]

        salary_response = g.supabase_user_client.from_('salary_components').select('id, base_salary, bonus, incentives').eq('employee_id', employee_id).is_('end_date', 'null').execute()
        gross_salary = sum(float(s['base_salary']) + float(s['bonus']) + float(s['incentives']) for s in salary_response.data) if salary_response.data else 0.0

        deductions_response = g.supabase_user_client.from_('deductions').select("*, default_charges(penalty_fee)").eq("employee_id", employee_id).eq('status', 'pending').execute()
        if not deductions_response.data:
            deductions_response.data = []


        for deduction in deductions_response.data:
            total_deductions += float(deduction['instances']) * float(deduction['default_charges']['penalty_fee']) - float(deduction['pardoned_fee'])
            deduction_ids.append(deduction['id'])
        # if deductions_response.data:
        #     total_deductions = float(deductions_response.data[0]['total_pardoned_fee'])
        #     deduction_ids = deductions_response.data[0]['deduction_ids']

        net_salary = gross_salary - total_deductions

        if gross_salary == 0 and total_deductions == 0:
            raise Exception(f"No salary or deductions found for employee {employee_id}.")
        
        payment_data = {
            'employee_id': str(employee_id),
            'payment_date': datetime.now().isoformat(),
            'month_year': period,
            'gross_salary': gross_salary,
            'total_deductions': total_deductions,
            'net_salary': net_salary,
            'created_by': created_by,
            'status': 'completed',  # Assuming status is 'completed' for generated payments
        }

        payment_response = g.supabase_user_client.from_('payment_history').insert(payment_data).execute() 

        if deduction_ids:
            update_response = g.supabase_user_client.from_('deductions').update({
                'payment_history_id': payment_response.data[0]['id'],
                "status": "paid"
            }).in_('id', deduction_ids).execute()
        
        # Update next_due_date (first day of next month)
        print(f"Updating next_due_date for employee {employee_id} to the 25th of next month.")
        next_due_date = next_due_date + relativedelta(months=1) if next_due_date else datetime.now() + relativedelta(months=1)
        next_due_date = next_due_date.replace(day=25)  # Set to the 25th
        update_employee = g.supabase_user_client.from_("employees").update({
            "next_due_date": next_due_date.date().isoformat()
        }).eq("id", employee_id).execute()
        payment_data["next_due_date"] = next_due_date.date().isoformat()
        
        return payment_data
    
    except Exception as e:
        traceback.print_exc()
        print(e)
        if payment_response and payment_response.data:
            # Rollback payment creation
            print(f"Rolling back payment creation for employee {employee_id}.")
            g.supabase_user_client.from_('payment_history').delete().eq('id', payment_response.data[0]['id']).execute()
        if deduction_ids:
            g.supabase_user_client.from_('deductions').update({
                'payment_history_id': None,
                "status": "pending"
            }).in_('id', deduction_ids).execute()
        
        current_app.logger.error(f"Error generating payment for employee {employee_id}: {str(e)}")
        raise e


def employee_payment_records(employee_id: str):
    """Fetch all payment records for a specific employee and associated deductions for each payment"""
    try:
        payments_response = g.supabase_user_client.from_('payment_history').select('*').eq('employee_id', employee_id).order('payment_date', desc=True).execute()
        if not payments_response.data:
            return []

        payment_records = payments_response.data

        for payment in payment_records:
            deductions_response = g.supabase_user_client.from_('deductions').select('*').eq('payment_history_id', payment['id']).execute()
            payment['deductions'] = deductions_response.data if deductions_response.data else []
        return payment_records

    except Exception as e:
        traceback.print_exc()
        current_app.logger.error(f"Error fetching payment records for employee {employee_id}: {str(e)}")
        raise e