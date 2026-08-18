import os
import re
import secrets
from datetime import datetime
from functools import wraps

from flask import (
    Flask, abort, flash, redirect, render_template, request,
    session, url_for
)
from sqlalchemy import or_
from werkzeug.exceptions import HTTPException

from config import Config
from models import db, User, Task, Announcement, Attendance, LeaveRequest, Payroll, Notification

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@gmail\.com$", re.I)
ROLES = {"owner", "manager", "employee"}
TASK_STATUSES = {"pending", "in_progress", "completed"}


def valid_gmail(email):
    return bool(EMAIL_RE.fullmatch((email or "").strip()))


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        session.clear()
        return None
    return user


@app.context_processor
def inject_globals():
    return {"current_user": current_user()}


@app.before_request
def ensure_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)


@app.context_processor
def inject_csrf():
    return {"csrf_token": session.get("csrf_token", "")}


def verify_csrf():
    if request.method == "POST":
        token = request.form.get("csrf_token", "")
        if not token or not secrets.compare_digest(token, session.get("csrf_token", "")):
            abort(400, description="Invalid or missing CSRF token.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("home"))
        return view(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            user = current_user()
            if user.role != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def role_dashboard(role):
    return {
        "owner": "owner_dashboard",
        "manager": "manager_dashboard",
        "employee": "employee_dashboard",
    }[role]


def get_or_404_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    return user


def validate_user_form(form, is_edit=False, existing_user=None, role=None):
    name = form.get("name", "").strip()
    email = form.get("email", "").strip().lower()
    phone = form.get("phone", "").strip()
    department = form.get("department", "").strip()
    designation = form.get("designation", "").strip()
    password = form.get("password", "")
    confirm = form.get("confirm_password", "")

    if not name:
        return "Full name is required."
    if not valid_gmail(email):
        return "Use a valid Gmail address such as user@gmail.com."
    query = User.query.filter_by(email=email)
    if existing_user:
        query = query.filter(User.id != existing_user.id)
    if query.first():
        return "That Gmail address is already registered."
    if not is_edit:
        if len(password) < 8:
            return "Password must be at least 8 characters."
        if password != confirm:
            return "Passwords do not match."
    elif password or confirm:
        if len(password) < 8:
            return "New password must be at least 8 characters."
        if password != confirm:
            return "Passwords do not match."

    if role not in {"manager", "employee"}:
        return "Invalid account role."
    return None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        verify_csrf()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not email or not message:
            flash("Please complete all contact fields.", "danger")
        else:
            flash("Thanks! Your message has been received.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")


def login_page(role):
    if request.method == "POST":
        verify_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email, role=role, is_active=True).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template(f"auth/{role}_login.html", role=role)

        session.clear()
        session["user_id"] = user.id
        session["role"] = user.role
        session["csrf_token"] = secrets.token_urlsafe(32)
        flash(f"Welcome, {user.name}!", "success")
        return redirect(url_for(role_dashboard(role)))

    return render_template(f"auth/{role}_login.html", role=role)


@app.route("/owner/login", methods=["GET", "POST"])
def owner_login():
    return login_page("owner")


@app.route("/manager/login", methods=["GET", "POST"])
def manager_login():
    return login_page("manager")


@app.route("/employee/login", methods=["GET", "POST"])
def employee_login():
    return login_page("employee")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    verify_csrf()
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


def notify(uid,title,msg):
    db.session.add(Notification(user_id=uid,title=title,message=msg))

def d(value):
    try: return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError,ValueError): return None

@app.route("/owner/attendance",methods=["GET","POST"])
@role_required("owner")
def owner_attendance():
    employees=User.query.filter_by(role="employee").order_by(User.name).all()
    if request.method=="POST":
        verify_csrf(); eid=request.form.get("employee_id",type=int); day=d(request.form.get("date")); e=db.session.get(User,eid)
        if not e or e.role!="employee" or not day: flash("Invalid employee/date.","danger")
        else:
            r=Attendance.query.filter_by(employee_id=e.id,date=day).first() or Attendance(employee_id=e.id,date=day)
            r.status=request.form.get("status","present"); r.check_in=request.form.get("check_in"); r.check_out=request.form.get("check_out"); r.notes=request.form.get("notes"); db.session.add(r); db.session.commit(); flash("Attendance saved.","success")
            notify(e.id,"Attendance updated",f"Attendance for {day} is {r.status}."); db.session.commit()
            return redirect(url_for("owner_attendance"))
    return render_template("owner/attendance.html",employees=employees,records=Attendance.query.order_by(Attendance.date.desc()).all())

@app.route("/owner/payroll",methods=["GET","POST"])
@role_required("owner")
def owner_payroll():
    employees=User.query.filter_by(role="employee").order_by(User.name).all()
    if request.method=="POST":
        verify_csrf(); eid=request.form.get("employee_id",type=int); e=db.session.get(User,eid); month=request.form.get("month")
        try: b=float(request.form.get("basic_salary",0)); a=float(request.form.get("allowances",0)); de=float(request.form.get("deductions",0))
        except ValueError: flash("Salary values must be numbers.","danger"); return redirect(url_for("owner_payroll"))
        if not e or e.role!="employee" or not month: flash("Invalid payroll data.","danger")
        else:
            r=Payroll.query.filter_by(employee_id=e.id,month=month).first() or Payroll(employee_id=e.id,month=month); r.basic_salary=b; r.allowances=a; r.deductions=de; r.net_salary=max(0,b+a-de); r.payment_status=request.form.get("payment_status","pending"); db.session.add(r); db.session.commit(); notify(e.id,"Payroll updated",f"Payroll for {month} is available."); db.session.commit(); flash("Payroll saved.","success"); return redirect(url_for("owner_payroll"))
    return render_template("owner/payroll.html",employees=employees,records=Payroll.query.order_by(Payroll.month.desc()).all())

@app.route("/owner/leaves")
@role_required("owner")
def owner_leaves(): return render_template("owner/leaves.html",leaves=LeaveRequest.query.order_by(LeaveRequest.id.desc()).all())

@app.route("/owner/leaves/<int:lid>/<action>",methods=["POST"])
@role_required("owner")
def owner_leave_action(lid,action):
    verify_csrf(); r=db.session.get(LeaveRequest,lid)
    if not r or action not in {"approve","reject"}: abort(404)
    r.status="approved" if action=="approve" else "rejected"; r.comment=request.form.get("comment",""); db.session.commit(); notify(r.employee_id,"Leave updated",f"Your leave request was {r.status}."); db.session.commit(); return redirect(url_for("owner_leaves"))

@app.route("/owner/reports")
@role_required("owner")
def owner_reports(): return render_template("owner/reports.html",employees=User.query.filter_by(role="employee").order_by(User.name).all())

@app.route("/owner/reports/<int:eid>")
@role_required("owner")
def owner_report(eid):
    e=db.session.get(User,eid)
    if not e or e.role!="employee": abort(404)
    att=Attendance.query.filter_by(employee_id=e.id).all(); leaves=LeaveRequest.query.filter_by(employee_id=e.id).all(); pay=Payroll.query.filter_by(employee_id=e.id).all(); tasks=Task.query.filter_by(employee_id=e.id).all()
    return render_template("report.html",employee=e,attendance=att,leaves=leaves,payroll=pay,tasks=tasks,back=url_for("owner_reports"))

@app.route("/manager/attendance",methods=["GET","POST"])
@role_required("manager")
def manager_attendance():
    me=current_user(); employees=User.query.filter_by(manager_id=me.id,role="employee").all()
    if request.method=="POST":
        verify_csrf(); eid=request.form.get("employee_id",type=int); e=db.session.get(User,eid); day=d(request.form.get("date"))
        if not e or e.manager_id!=me.id or not day: abort(403)
        r=Attendance.query.filter_by(employee_id=e.id,date=day).first() or Attendance(employee_id=e.id,date=day); r.status=request.form.get("status","present"); r.check_in=request.form.get("check_in"); r.check_out=request.form.get("check_out"); db.session.add(r); db.session.commit(); notify(e.id,"Attendance updated",f"Attendance for {day} is {r.status}."); db.session.commit(); return redirect(url_for("manager_attendance"))
    return render_template("manager/attendance.html",employees=employees,records=Attendance.query.filter(Attendance.employee_id.in_([e.id for e in employees])).order_by(Attendance.date.desc()).all() if employees else [])

@app.route("/manager/leaves")
@role_required("manager")
def manager_leaves():
    me=current_user(); ids=[e.id for e in User.query.filter_by(manager_id=me.id,role="employee").all()]; return render_template("manager/leaves.html",leaves=LeaveRequest.query.filter(LeaveRequest.employee_id.in_(ids)).order_by(LeaveRequest.id.desc()).all() if ids else [])

@app.route("/manager/leaves/<int:lid>/<action>",methods=["POST"])
@role_required("manager")
def manager_leave_action(lid,action):
    verify_csrf(); r=db.session.get(LeaveRequest,lid); e=db.session.get(User,r.employee_id) if r else None
    if not r or not e or e.manager_id!=current_user().id or action not in {"approve","reject"}: abort(403)
    r.status="approved" if action=="approve" else "rejected"; r.comment=request.form.get("comment",""); db.session.commit(); notify(e.id,"Leave updated",f"Your leave request was {r.status}."); db.session.commit(); return redirect(url_for("manager_leaves"))

@app.route("/manager/reports")
@role_required("manager")
def manager_reports(): return render_template("manager/reports.html",employees=User.query.filter_by(manager_id=current_user().id,role="employee").all())

@app.route("/manager/reports/<int:eid>")
@role_required("manager")
def manager_report(eid):
    e=db.session.get(User,eid)
    if not e or e.manager_id!=current_user().id: abort(403)
    return render_template("report.html",employee=e,attendance=Attendance.query.filter_by(employee_id=e.id).all(),leaves=LeaveRequest.query.filter_by(employee_id=e.id).all(),payroll=Payroll.query.filter_by(employee_id=e.id).all(),tasks=Task.query.filter_by(employee_id=e.id).all(),back=url_for("manager_reports"))

@app.route("/employee/attendance")
@role_required("employee")
def employee_attendance(): return render_template("employee/attendance.html",records=Attendance.query.filter_by(employee_id=current_user().id).order_by(Attendance.date.desc()).all())

@app.route("/employee/payroll")
@role_required("employee")
def employee_payroll(): return render_template("employee/payroll.html",records=Payroll.query.filter_by(employee_id=current_user().id).order_by(Payroll.month.desc()).all())

@app.route("/employee/leave",methods=["GET","POST"])
@role_required("employee")
def employee_leave():
    e=current_user()
    if request.method=="POST":
        verify_csrf(); start=d(request.form.get("start_date")); end=d(request.form.get("end_date")); reason=request.form.get("reason","")
        if not start or not end or end<start or not reason: flash("Enter valid dates and a reason.","danger")
        else:
            r=LeaveRequest(employee_id=e.id,leave_type=request.form.get("leave_type","casual"),start_date=start,end_date=end,reason=reason); db.session.add(r);
            if e.manager_id: notify(e.manager_id,"New leave request",f"{e.name} submitted a leave request.")
            db.session.commit(); flash("Leave request submitted.","success"); return redirect(url_for("employee_leave"))
    return render_template("employee/leave.html",leaves=LeaveRequest.query.filter_by(employee_id=e.id).order_by(LeaveRequest.id.desc()).all())

@app.route("/notifications")
@login_required
def notifications(): return render_template("notifications.html",notifications=Notification.query.filter_by(user_id=current_user().id).order_by(Notification.id.desc()).all())

@app.route("/notifications/read/<int:nid>",methods=["POST"])
@login_required
def notification_read(nid):
    verify_csrf(); n=db.session.get(Notification,nid)
    if not n or n.user_id!=current_user().id: abort(403)
    n.is_read=True; db.session.commit(); return redirect(url_for("notifications"))

# ---------------- OWNER ----------------

@app.route("/owner/dashboard")
@role_required("owner")
def owner_dashboard():
    return render_template(
        "owner/dashboard.html",
        managers=User.query.filter_by(role="manager").count(),
        employees=User.query.filter_by(role="employee").count(),
        active_users=User.query.filter_by(is_active=True).count(),
        tasks=Task.query.count(),
    )


@app.route("/owner/managers")
@role_required("owner")
def owner_managers():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(role="manager")
    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.name.ilike(like), User.email.ilike(like), User.department.ilike(like)))
    managers = query.order_by(User.created_at.desc()).all()
    return render_template("owner/managers.html", managers=managers, q=q)


@app.route("/owner/managers/create", methods=["GET", "POST"])
@role_required("owner")
def create_manager():
    if request.method == "POST":
        verify_csrf()
        error = validate_user_form(request.form, role="manager")
        if error:
            flash(error, "danger")
        else:
            user = User(
                name=request.form["name"].strip(),
                email=request.form["email"].strip().lower(),
                role="manager",
                phone=request.form.get("phone", "").strip(),
                department=request.form.get("department", "").strip(),
                designation=request.form.get("designation", "").strip(),
                is_active=True,
            )
            user.set_password(request.form["password"])
            db.session.add(user)
            db.session.commit()
            flash("Manager created successfully.", "success")
            return redirect(url_for("owner_managers"))
    return render_template("owner/create_manager.html")


@app.route("/owner/managers/edit/<int:user_id>", methods=["GET", "POST"])
@role_required("owner")
def edit_manager(user_id):
    manager = get_or_404_user(user_id)
    if manager.role != "manager":
        abort(404)

    if request.method == "POST":
        verify_csrf()
        error = validate_user_form(request.form, is_edit=True, existing_user=manager, role="manager")
        if error:
            flash(error, "danger")
        else:
            manager.name = request.form["name"].strip()
            manager.email = request.form["email"].strip().lower()
            manager.phone = request.form.get("phone", "").strip()
            manager.department = request.form.get("department", "").strip()
            manager.designation = request.form.get("designation", "").strip()
            if request.form.get("password"):
                manager.set_password(request.form["password"])
            db.session.commit()
            flash("Manager updated successfully.", "success")
            return redirect(url_for("owner_managers"))

    return render_template("owner/edit_manager.html", manager=manager)


@app.route("/owner/managers/delete/<int:user_id>", methods=["POST"])
@role_required("owner")
def delete_manager(user_id):
    verify_csrf()
    manager = get_or_404_user(user_id)
    if manager.role != "manager":
        abort(404)
    # Deactivate instead of hard deleting, preserving employee relationships.
    manager.is_active = False
    db.session.commit()
    flash("Manager deactivated.", "success")
    return redirect(url_for("owner_managers"))


@app.route("/owner/managers/activate/<int:user_id>", methods=["POST"])
@role_required("owner")
def activate_manager(user_id):
    verify_csrf()
    manager = get_or_404_user(user_id)
    if manager.role != "manager":
        abort(404)
    manager.is_active = True
    db.session.commit()
    flash("Manager activated.", "success")
    return redirect(url_for("owner_managers"))


@app.route("/owner/employees")
@role_required("owner")
def owner_employees():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(role="employee")
    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.name.ilike(like), User.email.ilike(like), User.department.ilike(like)))
    employees = query.order_by(User.created_at.desc()).all()
    return render_template("owner/employees.html", employees=employees, q=q)


@app.route("/owner/employees/create", methods=["GET", "POST"])
@role_required("owner")
def create_employee():
    managers = User.query.filter_by(role="manager", is_active=True).order_by(User.name).all()

    if request.method == "POST":
        verify_csrf()
        error = validate_user_form(request.form, role="employee")
        manager_id = request.form.get("manager_id", type=int)
        manager = db.session.get(User, manager_id) if manager_id else None
        if error:
            flash(error, "danger")
        elif not manager or manager.role != "manager" or not manager.is_active:
            flash("Please select an active manager.", "danger")
        else:
            employee = User(
                name=request.form["name"].strip(),
                email=request.form["email"].strip().lower(),
                role="employee",
                phone=request.form.get("phone", "").strip(),
                department=request.form.get("department", "").strip(),
                designation=request.form.get("designation", "").strip(),
                manager_id=manager.id,
                is_active=True,
            )
            employee.set_password(request.form["password"])
            db.session.add(employee)
            db.session.commit()
            flash("Employee created and assigned successfully.", "success")
            return redirect(url_for("owner_employees"))

    return render_template("owner/create_employee.html", managers=managers)


@app.route("/owner/employees/edit/<int:user_id>", methods=["GET", "POST"])
@role_required("owner")
def edit_employee(user_id):
    employee = get_or_404_user(user_id)
    if employee.role != "employee":
        abort(404)

    managers = User.query.filter_by(role="manager", is_active=True).order_by(User.name).all()

    if request.method == "POST":
        verify_csrf()
        error = validate_user_form(request.form, is_edit=True, existing_user=employee, role="employee")
        manager_id = request.form.get("manager_id", type=int)
        manager = db.session.get(User, manager_id) if manager_id else None

        if error:
            flash(error, "danger")
        elif not manager or manager.role != "manager" or not manager.is_active:
            flash("Please select an active manager.", "danger")
        else:
            employee.name = request.form["name"].strip()
            employee.email = request.form["email"].strip().lower()
            employee.phone = request.form.get("phone", "").strip()
            employee.department = request.form.get("department", "").strip()
            employee.designation = request.form.get("designation", "").strip()
            employee.manager_id = manager.id
            if request.form.get("password"):
                employee.set_password(request.form["password"])
            db.session.commit()
            flash("Employee updated successfully.", "success")
            return redirect(url_for("owner_employees"))

    return render_template("owner/edit_employee.html", employee=employee, managers=managers)


@app.route("/owner/employees/delete/<int:user_id>", methods=["POST"])
@role_required("owner")
def delete_employee(user_id):
    verify_csrf()
    employee = get_or_404_user(user_id)
    if employee.role != "employee":
        abort(404)
    employee.is_active = False
    db.session.commit()
    flash("Employee deactivated.", "success")
    return redirect(url_for("owner_employees"))


@app.route("/owner/employees/activate/<int:user_id>", methods=["POST"])
@role_required("owner")
def activate_employee(user_id):
    verify_csrf()
    employee = get_or_404_user(user_id)
    if employee.role != "employee":
        abort(404)
    employee.is_active = True
    db.session.commit()
    flash("Employee activated.", "success")
    return redirect(url_for("owner_employees"))


# ---------------- MANAGER ----------------

@app.route("/manager/dashboard")
@role_required("manager")
def manager_dashboard():
    manager = current_user()
    employees = User.query.filter_by(manager_id=manager.id, role="employee").all()
    task_count = Task.query.filter_by(manager_id=manager.id).count()
    return render_template("manager/dashboard.html", employees=employees, task_count=task_count)


@app.route("/manager/employees")
@role_required("manager")
def manager_employees():
    manager = current_user()
    employees = User.query.filter_by(manager_id=manager.id, role="employee").order_by(User.name).all()
    return render_template("manager/employees.html", employees=employees)


@app.route("/manager/profile", methods=["GET", "POST"])
@role_required("manager")
def manager_profile():
    manager = current_user()
    if request.method == "POST":
        verify_csrf()
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        department = request.form.get("department", "").strip()
        designation = request.form.get("designation", "").strip()
        if not name:
            flash("Name is required.", "danger")
        else:
            manager.name = name
            manager.phone = phone
            manager.department = department
            manager.designation = designation
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("manager_profile"))
    return render_template("manager/profile.html", manager=manager)


@app.route("/manager/tasks/create/<int:employee_id>", methods=["GET", "POST"])
@role_required("manager")
def manager_create_task(employee_id):
    manager = current_user()
    employee = get_or_404_user(employee_id)
    if employee.role != "employee" or employee.manager_id != manager.id:
        abort(403)

    if request.method == "POST":
        verify_csrf()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date_raw = request.form.get("due_date", "").strip()
        due_date = None
        if due_date_raw:
            try:
                due_date = datetime.strptime(due_date_raw, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid due date.", "danger")
        if title and (not due_date_raw or due_date):
            task = Task(
                title=title,
                description=description,
                employee_id=employee.id,
                manager_id=manager.id,
                due_date=due_date,
                status="pending",
            )
            db.session.add(task)
            db.session.commit()
            flash("Task created.", "success")
            return redirect(url_for("manager_employees"))
        flash("Task title is required.", "danger")

    return render_template("manager/create_task.html", employee=employee)


# ---------------- EMPLOYEE ----------------

@app.route("/employee/dashboard")
@role_required("employee")
def employee_dashboard():
    employee = current_user()
    tasks = Task.query.filter_by(employee_id=employee.id).order_by(Task.created_at.desc()).all()
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
    return render_template(
        "employee/dashboard.html",
        employee=employee,
        tasks=tasks,
        announcements=announcements,
    )


@app.route("/employee/profile", methods=["GET", "POST"])
@role_required("employee")
def employee_profile():
    employee = current_user()
    if request.method == "POST":
        verify_csrf()
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        if not name:
            flash("Name is required.", "danger")
        else:
            employee.name = name
            employee.phone = phone
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("employee_profile"))
    return render_template("employee/profile.html", employee=employee)


@app.route("/employee/tasks")
@role_required("employee")
def employee_tasks():
    employee = current_user()
    tasks = Task.query.filter_by(employee_id=employee.id).order_by(Task.created_at.desc()).all()
    return render_template("employee/tasks.html", tasks=tasks)


@app.route("/employee/tasks/update/<int:task_id>", methods=["POST"])
@role_required("employee")
def employee_update_task(task_id):
    verify_csrf()
    employee = current_user()
    task = db.session.get(Task, task_id)
    if not task or task.employee_id != employee.id:
        abort(403)
    status = request.form.get("status", "")
    if status not in TASK_STATUSES:
        flash("Invalid task status.", "danger")
    else:
        task.status = status
        db.session.commit()
        flash("Task status updated.", "success")
    return redirect(url_for("employee_tasks"))


# ---------------- ERROR HANDLERS ----------------

@app.errorhandler(403)
def forbidden(error):
    return render_template("errors/403.html"), 403


@app.errorhandler(404)
def not_found(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    db.session.rollback()
    return render_template("errors/500.html"), 500


@app.errorhandler(400)
def bad_request(error):
    return render_template("errors/400.html", message=getattr(error, "description", "Bad request.")), 400


def initialize_database():
    with app.app_context():
        db.create_all()

        # Enforce the business rule: exactly one owner account.
        owners = User.query.filter_by(role="owner").all()
        if not owners:
            owner = User(
                name=app.config["INITIAL_OWNER_NAME"],
                email=app.config["INITIAL_OWNER_EMAIL"],
                role="owner",
                is_active=True,
            )
            owner.set_password(app.config["INITIAL_OWNER_PASSWORD"])
            db.session.add(owner)
            db.session.commit()
        elif len(owners) > 1:
            raise RuntimeError("Database contains more than one owner. Manual correction is required.")


if __name__ == "__main__":
    initialize_database()
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
