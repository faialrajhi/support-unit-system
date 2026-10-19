from datetime import datetime
import io
import os
from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for, session
import pandas as pd
import requests
from supabase import Client, create_client

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "support_unit_secret_key_2026")

# =========================
# قائمة المستخدمين لوحدة الدعم المساندة
# =========================
USERS = {
    # المدير (Admin)
    "turky": {"password": "123", "name": "تركي عبدالعزيز", "role": "admin", "title": "مدير النظام", "can_edit": True},
    
    # المشرفين (تم منح محمد صلاحية التعديل الكامل، وباقي المشرفين عرض فقط)
    "mohd": {"password": "123", "name": "محمد", "role": "employee", "title": "مشرف / موظف دعم", "can_edit": True},
    "raja": {"password": "123", "name": "رجاء", "role": "supervisor", "title": "مشرفة", "can_edit": False},
    "hosam": {"password": "123", "name": "حسام", "role": "supervisor", "title": "مشرف", "can_edit": False},

    # الموظفين (Employees)
    "ibrahim": {"password": "123", "name": "ابراهيم بخاري", "role": "employee", "title": "موظف دعم", "can_edit": True},
    "saleh": {"password": "123", "name": "صالح حنيف", "role": "employee", "title": "موظف دعم", "can_edit": True},
    "ahlam": {"password": "123", "name": "احلام هوساوي", "role": "employee", "title": "موظفة دعم", "can_edit": True},
    "maatouq": {"password": "123", "name": "معتوق سيف", "role": "employee", "title": "موظف دعم", "can_edit": True},
    "saleem": {"password": "123", "name": "سليم الشريف", "role": "employee", "title": "موظف دعم", "can_edit": True},
    "fowzi": {"password": "123", "name": "فوزي بليلة", "role": "employee", "title": "موظف دعم", "can_edit": True},
    "rami": {"password": "123", "name": "رامي اللقماني", "role": "employee", "title": "موظف دعم", "can_edit": True}
}

# =========================
# Supabase Configuration
# =========================
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://urnawuapfkhxvqvepzit.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVybmF3dWFwZmtoeHZxdmVweml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4ODA5NTQxMCwiZXhwIjoyMTAzNjcxNDEwfQ.hg8Ki6qvoI_Fhammt_87t-HfTZPSdvl6nYn5bUtThzo")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# Green API Configuration
# =========================
GREEN_API_INSTANCE_ID = os.environ.get("GREEN_API_INSTANCE_ID", "710722772629")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN2", os.environ.get("GREEN_API_TOKEN", "e2ff31ea0b24f838a230552e4acabd61fd93c37be6d408ebd"))
WHATSAPP_GROUP_ID = os.environ.get("WHATSAPP_GROUP_ID", "120363044377285466@g.us")


def get_next_record_number():
    """يحسب رقم السجل التالي بدقة بناءً على السجلات الفعلية + 1"""
    try:
        response = supabase.table("support_unit_records").select("id", count="exact").execute()
        total_records = len(response.data) if response.data else 0
        return total_records + 1
    except Exception as e:
        print("Error calculating record number:", e)
        return 1


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        if username in USERS and USERS[username]["password"] == password:
            session["user"] = username
            session["employee_name"] = USERS[username]["name"]
            session["role"] = USERS[username]["role"]
            session["can_edit"] = USERS[username]["can_edit"]
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="اسم المستخدم أو كلمة المرور غير صحيحة")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        if not session.get("can_edit", True):
            return jsonify({"success": False, "message": "غير مصرح لك بإضافة أو تعديل البيانات"}), 403

        form_data = request.form
        logged_emp_name = session.get("employee_name", "موظف النظام")

        record = {
            "patient_name": form_data.get("patient_name"),
            "national_id": form_data.get("national_id", "-"),
            "file_number": form_data.get("file_number", "-"),
            "patient_phone": form_data.get("patient_phone", "-"),
            "service_type": form_data.get("service_type"),
            "department": form_data.get("department"),
            "notes": form_data.get("notes", "-"),
            "employee_name": logged_emp_name,
            "record_date": form_data.get("record_date"),
            "record_time": form_data.get("record_time")
        }
        try:
            supabase.table("support_unit_records").insert(record).execute()
            return redirect(url_for("index"))
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    try:
        response = supabase.table("support_unit_records").select("*").order("id", desc=True).execute()
        records = response.data or []
    except Exception as e:
        records = []

    return render_template(
        "index.html", 
        records=records, 
        logged_employee=session.get("employee_name"),
        can_edit=session.get("can_edit", True),
        user_role=session.get("role")
    )


if __name__ == "__main__":
    app.run(debug=True)
