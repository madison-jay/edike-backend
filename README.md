Below is a comprehensive Markdown documentation for the employee-related endpoints of your Flask and Supabase-based ERP API. This documentation is tailored for your frontend team, providing clear instructions on how to interact with the API, including endpoint details, authentication requirements, request/response formats, and error handling.

---

# ERP API Documentation for Employee Management

This document outlines the employee management endpoints for the ERP backend API, built with Flask and Supabase. These endpoints allow the frontend to retrieve, create, update, and soft-delete employee records. The API uses JSON Web Tokens (JWT) for authentication and Supabase’s Row-Level Security (RLS) to enforce access control based on user roles.

## Base URL

- **BASE_URL**: `http://domain.com/api/v1/`

All endpoints are prefixed with `/employees`.

## Authentication

All endpoints require authentication via a JWT in the `Authorization` header and `X-Refresh-Token`. The token must be obtained from Supabase’s authentication system (e.g., via `signInWithEmail`).

- **Header Format**:
  ```
  Authorization: Bearer <jwt-token>
  X-Refresh-Token: <refresh_token>
  ```
- **Obtaining a JWT**:
  - Use the Supabase JavaScript SDK to sign in:
    ```javascript
    import { createClient } from "@supabase/supabase-js";
    const supabase = createClient(
      "https://<your-supabase-url>.supabase.co",
      "<your-supabase-key>"
    );
    const { data, error } = await supabase.auth.signInWithPassword({
      email: "user@example.com",
      password: "password123",
    });
    const token = data.session.access_token;
    ```
  - Store the token securely and include it in all API requests.
- **Roles**:
  - The JWT’s `user_metadata.role` determines access. Supported roles are:
    - `super_admin`: Full access to all employees and roles.
    - `hr_manager`: Can manage most employees but cannot create/promote to `super_admin`.
    - `manager`: Can view employees in their department (per RLS).
    - `user`: Can view/update their own record (per RLS).

## Endpoints

### 1. Get All Employees

Retrieve a list of employees, filtered by the authenticated user’s role via Supabase RLS.

- **Endpoint**: `GET /employees`
- **Access**: Requires authentication. Allowed roles: `super_admin`, `hr_manager`, `manager`, `user`, or `null` (limited access).
- **Description**:
  - `super_admin`, `hr_manager`: Returns all employees.
  - `manager`: Returns employees in their department.
  - `user`: Returns only the user’s own record.
  - `null`: Returns basic employee info (if allowed by RLS) or an empty array.

#### Request

- **Method**: GET
- **URL**: `{{base_url}}/employees`
- **Headers**:
  ```
  Authorization: Bearer <jwt-token>
  ```
- **Body**: None

#### Response

- **Success (200 OK)**:
  ```json
  [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "user_id": "456e7890-e89b-12d3-a456-426614174001",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "department": "Engineering",
      "employment_status": "active",
      "created_at": "2025-07-10T12:00:00Z",
      "deleted_at": null
    },
    ...
  ]
  ```
  _Note_: Fields depend on the `employees` table schema and RLS policies.
- **Empty Result (404 Not Found)**:
  ```json
  {
    "message": "No employees found"
  }
  ```
- **Unauthorized (401)**:
  ```json
  {
    "error": "Unauthorized"
  }
  ```
- **Internal Server Error (500)**:
  ```json
  {
    "error": "<error-details>"
  }
  ```

#### Example

```javascript
fetch("http://localhost:5000/employees", {
  method: "GET",
  headers: {
    Authorization: "Bearer <jwt-token>",
  },
})
  .then((response) => response.json())
  .then((data) => console.log(data))
  .catch((error) => console.error("Error:", error));
```

---

### 2. Get Single Employee

Retrieve a specific employee by their ID, with access controlled by RLS.

- **Endpoint**: `GET /employees/<employee_id>`
- **Access**: Requires authentication. Allowed roles: `super_admin`, `hr_manager`, `manager`, `user`.
- **Description**:
  - Returns the employee’s record if the user has permission (e.g., `user` can only access their own record).
  - `employee_id` must be a valid UUID.

#### Request

- **Method**: GET
- **URL**: `{{base_url}}/employees/<employee_id>`
- **Headers**:
  ```
  Authorization: Bearer <jwt-token>
  ```
- **Body**: None
- **Parameters**:
  - `employee_id` (path): UUID of the employee (e.g., `123e4567-e89b-12d3-a456-426614174000`).

#### Response

- **Success (200 OK)**:
  ```json
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "456e7890-e89b-12d3-a456-426614174001",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "department": "Engineering",
    "employment_status": "active",
    "created_at": "2025-07-10T12:00:00Z",
    "deleted_at": null
  }
  ```
- **Invalid UUID (400 Bad Request)**:
  ```json
  {
    "error": "Invalid employee ID format"
  }
  ```
- **Not Found (404)**:
  ```json
  {
    "error": "Employee not found"
  }
  ```
- **Unauthorized (401)**:
  ```json
  {
    "error": "Unauthorized"
  }
  ```
- **Forbidden (403)**:
  ```json
  {
    "error": "Forbidden"
  }
  ```
- **Internal Server Error (500)**:
  ```json
  {
    "error": "<error-details>"
  }
  ```

#### Example

```javascript
fetch("http://localhost:5000/employees/123e4567-e89b-12d3-a456-426614174000", {
  method: "GET",
  headers: {
    Authorization: "Bearer <jwt-token>",
  },
})
  .then((response) => response.json())
  .then((data) => console.log(data))
  .catch((error) => console.error("Error:", error));
```

---

### 3. Create Employee

Create a new employee record and associated Supabase auth user.

- **Endpoint**: `POST /employees`
- **Access**: Requires authentication. Allowed roles: `super_admin`, `hr_manager`.
- **Description**:
  - Creates an employee in the `employees` table and a corresponding user in Supabase Auth.
  - `hr_manager` cannot create users with the `super_admin` role.
  - Input is validated using Pydantic’s `EmployeeCreateSchema`.

#### Request

- **Method**: POST
- **URL**: `{{base_url}}/employees`
- **Headers**:
  ```
  Authorization: Bearer <jwt-token>
  Content-Type: application/json
  ```
- **Body** (JSON):
  ```json
  {
    "email": "new_employee@example.com",
    "password": "password123",
    "first_name": "Jane",
    "last_name": "Smith",
    "department": "Marketing",
    "initial_role": "user",
    "employment_status": "active"
  }
  ```
  _Note_: Required fields depend on `EmployeeCreateSchema`. Share the schema for exact requirements.

#### Response

- **Success (201 Created)**:
  ```json
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "456e7890-e89b-12d3-a456-426614174001",
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "new_employee@example.com",
    "department": "Marketing",
    "employment_status": "active",
    "created_at": "2025-07-10T12:00:00Z",
    "deleted_at": null
  }
  ```
- **Bad Request (400)**:
  ```json
  {
    "error": "Validation failed",
    "details": [
      {
        "loc": ["email"],
        "msg": "value is not a valid email address",
        "type": "value_error.email"
      }
    ]
  }
  ```
- **Forbidden (403)**:
  ```json
  {
    "error": "HR Manager cannot create Super Admin users"
  }
  ```
- **Unauthorized (401)**:
  ```json
  {
    "error": "Unauthorized"
  }
  ```
- **Internal Server Error (500)**:
  ```json
  {
    "error": "<error-details>"
  }
  ```

#### Example

```javascript
fetch("http://localhost:5000/employees", {
  method: "POST",
  headers: {
    Authorization: "Bearer <jwt-token>",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    email: "new_employee@example.com",
    password: "password123",
    first_name: "Jane",
    last_name: "Smith",
    department: "Marketing",
    initial_role: "user",
    employment_status: "active",
  }),
})
  .then((response) => response.json())
  .then((data) => console.log(data))
  .catch((error) => console.error("Error:", error));
```

---

### 4. Update Employee

Update an existing employee record, with field restrictions enforced by RLS for `user` role.

- **Endpoint**: `PUT /employees/<employee_id>`
- **Access**: Requires authentication. Allowed roles: `super_admin`, `hr_manager`, `user`.
- **Description**:
  - `super_admin`, `hr_manager`: Can update any employee’s fields and role (except `hr_manager` cannot promote to `super_admin`).
  - `user`: Can update their own record (limited fields, enforced by RLS).
  - Input is validated using Pydantic’s `EmployeeUpdateSchema`.

#### Request

- **Method**: PUT
- **URL**: `{{base_url}}/employees/<employee_id>`
- **Headers**:
  ```
  Authorization: Bearer <jwt-token>
  Content-Type: application/json
  ```
- **Parameters**:
  - `employee_id` (path): UUID of the employee.
- **Body** (JSON):
  ```json
  {
    "first_name": "Jane",
    "last_name": "Smith",
    "department": "Sales",
    "role": "manager"
  }
  ```
  _Note_: `role` is optional and ignored for `user` role updates. Share `EmployeeUpdateSchema` for exact fields.

#### Response

- **Success (200 OK)**:
  ```json
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "456e7890-e89b-12d3-a456-426614174001",
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "employee@example.com",
    "department": "Sales",
    "employment_status": "active",
    "created_at": "2025-07-10T12:00:00Z",
    "deleted_at": null
  }
  ```
- **Invalid UUID (400)**:
  ```json
  {
    "error": "Invalid employee ID format"
  }
  ```
- **Validation Error (400)**:
  ```json
  {
    "error": "Validation failed",
    "details": [
      {
        "loc": ["department"],
        "msg": "value not in allowed departments",
        "type": "value_error"
      }
    ]
  }
  ```
- **Forbidden (403)**:
  ```json
  {
    "error": "HR Managers cannot promote users to Super Admin"
  }
  ```
  or
  ```json
  {
    "error": "Users are not allowed to change their own role"
  }
  ```
  or
  ```json
  {
    "message": "Permission denied: You can only update your own record"
  }
  ```
- **Unauthorized (401)**:
  ```json
  {
    "error": "Unauthorized"
  }
  ```
- **Not Found (500)** (Note: Should be 404, consider updating backend):
  ```json
  {
    "error": "Failed to update employee or employee not found"
  }
  ```
- **Internal Server Error (500)**:
  ```json
  {
    "error": "<error-details>"
  }
  ```

#### Example

```javascript
fetch("http://localhost:5000/employees/123e4567-e89b-12d3-a456-426614174000", {
  method: "PUT",
  headers: {
    Authorization: "Bearer <jwt-token>",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    first_name: "Jane",
    last_name: "Smith",
    department: "Sales",
    role: "manager",
  }),
})
  .then((response) => response.json())
  .then((data) => console.log(data))
  .catch((error) => console.error("Error:", error));
```

---

### 5. Soft-Delete Employee

Soft-delete an employee by setting `employment_status` to `terminated` and populating `deleted_at`.

- **Endpoint**: `DELETE /employees/<employee_id>`
- **Access**: Requires authentication. Allowed roles: `super_admin`, `hr_manager`.
- **Description**:
  - Marks the employee as terminated without deleting the Supabase Auth user.
  - Uses `service_supabase_client` to bypass RLS for administrative updates.

#### Request

- **Method**: DELETE
- **URL**: `{{base_url}}/employees/<employee_id>`
- **Headers**:
  ```
  Authorization: Bearer <jwt-token>
  ```
- **Parameters**:
  - `employee_id` (path): UUID of the employee.
- **Body**: None

#### Response

- **Success (200 OK)**:
  ```json
  {
    "message": "Employee 123e4567-e89b-12d3-a456-426614174000 deleted (terminated) successfully"
  }
  ```
- **Invalid UUID (400)**:
  ```json
  {
    "error": "Invalid employee ID format"
  }
  ```
- **Unauthorized (401)**:
  ```json
  {
    "error": "Unauthorized"
  }
  ```
- **Forbidden (403)**:
  ```json
  {
    "error": "Forbidden"
  }
  ```
- **Not Found (500)** (Note: Should be 404, consider updating backend):
  ```json
  {
    "error": "Failed to soft-delete employee or employee not found"
  }
  ```
- **Internal Server Error (500)**:
  ```json
  {
    "error": "<error-details>"
  }
  ```

#### Example

```javascript
fetch("http://localhost:5000/employees/123e4567-e89b-12d3-a456-426614174000", {
  method: "DELETE",
  headers: {
    Authorization: "Bearer <jwt-token>",
  },
})
  .then((response) => response.json())
  .then((data) => console.log(data))
  .catch((error) => console.error("Error:", error));
```

---

## Error Handling

- **401 Unauthorized**: Missing or invalid JWT. Ensure the token is valid and not expired.
- **403 Forbidden**: User lacks the required role or RLS denies access. Check the JWT’s `user_metadata.role` and Supabase RLS policies.
- **400 Bad Request**: Invalid input (e.g., malformed UUID or JSON failing Pydantic validation). Check the `details` field for specifics.
- **404 Not Found**: Resource not found (e.g., employee doesn’t exist or no employees match RLS).
- **500 Internal Server Error**: Unexpected server issue. Check the backend logs for details.
