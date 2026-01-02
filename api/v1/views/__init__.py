from flask import Blueprint

# Initialize the Blueprint for API v1 views
app_views = Blueprint('base', __name__, url_prefix='/api/v1')

from api.v1.views.hr import employees
from api.v1.views.hr import leave_requests
from api.v1.views.hr import shift_type
from api.v1.views.hr import tasks
from api.v1.views.hr import defaults
from api.v1.views.hr import deductions
from api.v1.views.hr import employee_payments
from api.v1.views.inventories import products
from api.v1.views.inventories import components
from api.v1.views.inventories import suppliers
from api.v1.views.inventories import stocks
from api.v1.views.inventories import import_batches
from api.v1.views.sales import orders
from api.v1.views.sales import customers
from api.v1.views.hr.knowledge_sharing import modules
from api.v1.views.hr.knowledge_sharing import lessons
from api.v1.views.hr.knowledge_sharing import questions
from api.v1.views.hr.kpi import kpi_templates
from api.v1.views.hr.kpi import employee_kpi_assignments
from api.v1.views.hr import attendance_bio