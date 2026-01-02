from datetime import datetime, time, timedelta
import json
import requests
from dotenv import load_dotenv
from os import getenv
from flask import g
import supabase

load_dotenv()


def calculate_status(emp_id, date, check_in, check_out):
    """
    Returns a LIST of applicable statuses (can be multiple)
    Possible: 'late', 'early-departure', 'absent', 'on-leave', 'half-day', 'in-time'
    """
    date_time = datetime.fromisoformat(f"{date} 00:00:00")
    date_only = date_time.date()

    # Fetch shift (same as before)
    shift_schedule = g.supabase_user_client.from_("shift_schedules")\
        .select("shift_type_id").eq("employee_id", emp_id)\
        .gte("start_date", date).lte("end_date", date).execute()

    if not shift_schedule.data:
        shift_start = time(9, 0)
        shift_end = time(17, 0)
    else:
        shift_type_id = shift_schedule.data[0]["shift_type_id"]
        shift_type = g.supabase_user_client.from_("shift_types")\
            .select("start_time", "end_time").eq("id", shift_type_id).execute()
        if shift_type.data:
            shift_start = time.fromisoformat(shift_type.data[0]["start_time"])
            shift_end = time.fromisoformat(shift_type.data[0]["end_time"])
        else:
            shift_start = time(9, 0)
            shift_end = time(17, 0)

    # Check leave
    leave_requests = g.supabase_user_client.from_("leave_requests")\
        .select("start_date", "end_date").eq("employee_id", emp_id)\
        .eq("status", "approved").execute()

    on_leave = any(
        date_only >= datetime.fromisoformat(l["start_date"]).date() and 
        date_only <= datetime.fromisoformat(l["end_date"]).date() 
        for l in leave_requests.data
    ) if leave_requests.data else False

    if on_leave:
        return ["on-leave"]

    if not check_in and not check_out:
        return ["absent"]

    statuses = []

    check_in_time = datetime.fromisoformat(check_in).time() if check_in else None
    check_out_time = datetime.fromisoformat(check_out).time() if check_out else None

    grace_period = timedelta(minutes=30)
    late_threshold = (datetime.combine(date_only, shift_start) + grace_period).time()
    early_threshold = (datetime.combine(date_only, shift_end) - grace_period).time()

    # Check Late
    if check_in_time and check_in_time > late_threshold:
        statuses.append("late")

    # Check Early Departure
    if check_out_time and check_out_time < early_threshold:
        statuses.append("early-departure")

    # Check for Half-Day (e.g., worked < 4 hours)
    if check_in_time and check_out_time:
        worked_duration = datetime.combine(date_only, check_out_time) - datetime.combine(date_only, check_in_time)
        if worked_duration < timedelta(hours=4):
            statuses.append("half-day")

    # Only add "in-time" if no negative statuses
    if not statuses and check_in_time and check_out_time:
        if check_in_time <= shift_start and check_out_time >= shift_end:
            statuses.append("in-time")

    # Fallback: if somehow no status, mark as present but incomplete
    if not statuses:
        statuses.append("present") 

    return statuses


class BiometricService:
    ZKTECO_URL = getenv("ZKTECO_SERVICE_URL")
    
    def __init__(self):
        self.base_url = self.ZKTECO_URL
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': "JWT " + self.get_api_token()
        }
    
    @staticmethod
    def get_api_token():
        """Retrieve API token from ZKTeco service"""
        url = f"{BiometricService.ZKTECO_URL}/jwt-api-token-auth/"
        
        payload = {
            "username": getenv("ZKTECO_API_USERNAME"),
            "password": getenv("ZKTECO_API_PASSWORD")
        }
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json().get('token')
        else:
            raise Exception(f"Failed to retrieve API token: {response.text}")
        
    
    def create_biometric_employee(self, emp_code, first_name, last_name):
        """Create a new employee biometric record in the ZKTeco system"""
        url = f"{self.base_url}/personnel/api/employees/"
        employee_data = {
            "first_name": first_name,
            "last_name": last_name,
            "department": 1,
            "area": [2],
            "emp_code": emp_code
        }
        response = requests.post(url, headers=self.headers, data=json.dumps(employee_data))
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create employee: {response.text}")
        
    def delete_biometric_employee(self, emp_id):
        """Delete an employee biometric record from the ZKTeco system"""
        url = f"{self.base_url}/personnel/api/employees/{emp_id}/"
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 204:
            return {"message": f"Employee {emp_id} deleted successfully"}
        else:
            raise Exception(f"Failed to delete employee: {response.text}")


    def sync_attendance(self, start_date, end_date):
        # Convert to date objects
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        date_range = [start_dt + timedelta(days=x) for x in range((end_dt - start_dt).days + 1)]

        # Step 1: Fetch ALL active employees (you may want to filter by active status)
        employees_response = g.supabase_user_client.from_("employees")\
            .select("id, biotime_id")\
            .neq("biotime_id", None)\
            .eq("employment_status", "active")\
            .execute()

        if not employees_response.data:
            return {"message": "No employees found"}

        # Build map: biotime_id -> internal emp_id
        biotime_to_emp_id = {str(emp["biotime_id"]): str(emp["id"]) for emp in employees_response.data if emp["biotime_id"]}

        #Initialize attendance records for ALL employees x ALL dates → default absent
        attendance_records = {}
        for emp_id in biotime_to_emp_id.values():
            attendance_records[emp_id] = {}
            for date_obj in date_range:
                date_str = date_obj.isoformat()
                attendance_records[emp_id][date_str] = {
                    "check_in": None,
                    "check_out": None,
                    "biotime_id": next(bid for bid, eid in biotime_to_emp_id.items() if eid == emp_id)
                }

        #Fetch punch transactions from BioTime
        url = f"{self.base_url}/iclock/api/transactions/?start_time={start_date} 00:00:00&end_time={end_date} 23:59:59&page_size=1000"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to sync attendance: {response.text}")

        transactions = response.json().get("data", [])

        #Overlay actual punches
        for trans in transactions:
            emp_code = trans.get("emp_code")
            if not emp_code or str(emp_code) not in biotime_to_emp_id:
                continue  # Skip unknown employees

            emp_id = biotime_to_emp_id[str(emp_code)]
            punch_time = trans.get("punch_time")
            if not punch_time:
                continue

            date_str = punch_time.split(" ")[0]
            if date_str not in [d.isoformat() for d in date_range]:
                continue  # Outside range

            punch_state = trans.get("punch_state_display", "").lower()

            if emp_id not in attendance_records:
                attendance_records[emp_id] = {}
            if date_str not in attendance_records[emp_id]:
                attendance_records[emp_id][date_str] = {"check_in": None, "check_out": None, "biotime_id": emp_code}

            record = attendance_records[emp_id][date_str]

            if "check-in" in punch_state or punch_state == "checkin":
                if record["check_in"] is None or punch_time < record["check_in"]:
                    record["check_in"] = punch_time
            elif "check-out" in punch_state or punch_state == "checkout":
                if record["check_out"] is None or punch_time > record["check_out"]:
                    record["check_out"] = punch_time

        #Save ALL records (present, late, absent, etc.)
        for emp_id, dates in attendance_records.items():
            for date_str, attendance in dates.items():
                check_in = attendance["check_in"]
                check_out = attendance["check_out"]

                status = calculate_status(emp_id, date_str, check_in, check_out)

                data = {
                    "employee_id": emp_id,
                    "date": date_str,
                    "check_in": check_in,
                    "check_out": check_out,
                    "status": status,
                    "biotime_id": str(attendance["biotime_id"])
                }

                
                existing = g.supabase_user_client.from_("attendance_transactions")\
                    .select("id")\
                    .eq("biotime_id", str(attendance["biotime_id"]))\
                    .eq("date", date_str)\
                    .execute()

                if existing.data:
                    g.supabase_user_client.from_("attendance_transactions")\
                        .update(data)\
                        .eq("id", existing.data[0]["id"])\
                        .execute()
                else:
                    g.supabase_user_client.from_("attendance_transactions")\
                        .insert(data)\
                        .execute()

        return {"message": f"Attendance synced successfully for {len(attendance_records)} employees from {start_date} to {end_date}"}



if __name__ == "__main__":
    service = BiometricService()
    transaction = service.get_transactions(start_date="2025-11-13", end_date="2025-11-13")
    print(transaction)