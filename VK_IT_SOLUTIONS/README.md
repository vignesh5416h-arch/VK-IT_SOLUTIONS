# VK IT SOLUTIONS — Flask Management Website

## Stack
- HTML5 / CSS3 / JavaScript
- Python Flask
- Flask-SQLAlchemy / SQLAlchemy ORM
- SQLite
- Werkzeug password hashing
- Session authentication
- CSRF token protection
- Strict server-side role authorization

## 1. Create virtual environment

### Windows
```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure environment

Edit `.env`.

The initial Owner is configurable:

```env
INITIAL_OWNER_EMAIL=owner@gmail.com
INITIAL_OWNER_PASSWORD=Owner@123
INITIAL_OWNER_NAME=VK IT Solutions Owner
SECRET_KEY=replace-with-a-long-random-secret
```

For production, generate a strong secret key and set:

```env
SESSION_COOKIE_SECURE=true
FLASK_DEBUG=false
```

Use HTTPS when `SESSION_COOKIE_SECURE=true`.

## 4. Initialize database

No separate migration command is required for this starter application.

Run:

```bash
python app.py
```

On startup, `initialize_database()` runs `db.create_all()` and creates the Owner only if no Owner exists.

Business rule:
- If zero owners exist → exactly one initial Owner is created.
- If one Owner exists → no second Owner is created.
- If the database contains more than one Owner → startup stops with an error so the data can be corrected manually.

The SQLite file is:

`vk_it_solutions.db`

## 5. Run

```bash
python app.py
```

Open:

`http://127.0.0.1:5000`

## 6. Login as Owner

Go to:

`/owner/login`

Default development credentials from `.env`:

- Email: `owner@gmail.com`
- Password: `Owner@123`

Change these before real deployment.

## 7. Create Managers

Owner login → Owner Dashboard → Create Manager.

A manager must have:
- Full Name
- unique Gmail address
- password + confirmation
- phone
- department
- designation

Only the Owner can create managers.

## 8. Create Employees

Owner login → Owner Dashboard → Create Employee.

Choose an active manager from the assignment list.

Only the Owner can create employees.

## 9. Manager login

Go to:

`/manager/login`

Use the Gmail/password created by the Owner.

A Manager can:
- see assigned employees
- view profile
- create tasks for assigned employees
- never access Owner routes

## 10. Employee login

Go to:

`/employee/login`

Use the Gmail/password created by the Owner.

An Employee can:
- view assigned manager
- view tasks
- update task status
- update permitted profile information
- never access Owner or Manager routes

## Authorization model

Every protected route uses server-side decorators:

- `@role_required("owner")`
- `@role_required("manager")`
- `@role_required("employee")`

The application does not depend on hiding buttons for security.

## Password storage

Only `password_hash` is stored in the database. Plain-text passwords are never stored.

## Important deployment note

This is a strong local/project starter. For public production deployment, add HTTPS, reverse proxy configuration, rate limiting, audit logging, production secret management, database migrations, email verification/password reset, and a real contact-message persistence or mail service.

## Premium modules added
- Attendance for Owner, Manager and Employee
- Monthly salary/payroll with automatic net salary calculation
- Employee leave requests and manager/owner approval
- Employee reports covering attendance, leave, payroll and tasks
- Per-user notifications and mark-as-read
- Expanded dashboard navigation and statistics

The new tables are created automatically by `db.create_all()` when `python app.py` starts.
