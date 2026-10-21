from datetime import datetime, timedelta
import io
import os
import re
import requests
from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for, session
import pandas as pd
from supabase import Client, create_client

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "support_unit_secret_key_2026")

# =========================
# Green API Configuration
# =========================
GREEN_API_INSTANCE_ID = os.environ.get("GREEN_API_INSTANCE_ID", "710722772629")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN", "2e2ff31ea0b24f838a230552e4acabd61fd93c37be6d408ebd")

def send_whatsapp_green_api(phone, patient_name, service_type, national_id, department, target_employee, logged_emp_name):
    """دالة لإرسال رسالة واتساب بتنسيق محدد ومباشر للمريض عبر Green API"""
    if not phone or str(phone).strip() in ["-", ""]:
        return

    # استخراج الأرقام فقط وحذف أي مسافات أو رموز
    clean_phone = re.sub(r'\D', '', str(phone).strip())

    # تحويل الرقم إلى الصيغة الدولية السعودية (966)
    if clean_phone.startswith("05"):
        clean_phone = "966" + clean_phone[1:]
    elif clean_phone.startswith("5") and len(clean_phone) == 9:
        clean_phone = "966" + clean_phone
    elif clean_phone.startswith("00966"):
        clean_phone = clean_phone[5:]

    url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"

    # إعداد نص الرسالة بتنسيق المباشر المحدد
    lines = [
        f"اسم المستفيد: {patient_name or '-'}",
        f"رقم الهوية: {national_id or '-'}",
        f"رقم الجوال: {phone or '-'}",
        f"الخدمة: {service_type or '-'}",
        f"القسم: {department or '-'}",
        f"الموظف المعني: {target_employee or '-'}",
        f"موظف تجربة المريض: {logged_emp_name or '-'}"
    ]
    message_text = "\n".join(lines)

    payload = {
        "chatId": f"{clean_phone}@c.us",
        "message": message_text
    }
    headers = {'Content-Type': 'application/json; charset=utf-8'}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print("Green API Status Code:", response.status_code)
        print("Green API Response:", response.text)
    except Exception as e:
        print("خطأ أثناء إرسال رسالة الواتساب عبر Green API:", e)

# =========================
# قائمة المستخدمين
# =========================
USERS = {
    # المدير (Admin)
    "turky": {"password": "123", "name": "تركي عبدالعزيز", "role": "admin", "title": "مدير النظام", "can_edit": True},
    
    # المشرفين
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
    "rami": {"password": "123", "name": "رامي اللقماني", "role": "employee", "title": "موظف دعم", "can_edit": True},

    # حسابات المتطوعين ومتدربي تمهير
    "tatwa1": {"password": "123", "name": "تطوع1", "role": "employee", "title": "متطوع", "can_edit": True},
    "tatwa2": {"password": "123", "name": "تطوع2", "role": "employee", "title": "متطوع", "can_edit": True},
    "tamheer1": {"password": "123", "name": "تمهير1", "role": "employee", "title": "متدرب تمهير", "can_edit": True},
    "tamheer2": {"password": "123", "name": "تمهير2", "role": "employee", "title": "متدرب تمهير", "can_edit": True},
    "tadreeb1": {"password": "123", "name": "تدريب1", "role": "employee", "title": "متدرب", "can_edit": True},
    "tadreeb2": {"password": "123", "name": "تدريب2", "role": "employee", "title": "متدرب", "can_edit": True}
}

VOLUNTEER_ACCOUNTS = ["tatwa1", "tatwa2", "tamheer1", "tamheer2", "tadreeb1", "tadreeb2"]

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://urnawuapfkhxvqvepzit.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVybmF3dWFwZmtoeHZxdmVweml0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4ODA5NTQxMCwiZXhwIjoyMTAzNjcxNDEwfQ.hg8Ki6qvoI_Fhammt_87t-HfTZPSdvl6nYn5bUtThzo")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        username = session.get("user", "")
        logged_emp_name = session.get("employee_name", "موظف النظام")

        # إذا كان الحساب يخص متطوع أو متدرب، يتم دمج اسمه الفعلي المدخل مع اسم الحساب
        if username in VOLUNTEER_ACCOUNTS:
            actual_name = form_data.get("actual_volunteer_name", "").strip()
            if actual_name:
                logged_emp_name = f"{actual_name} ({session.get('employee_name')})"

        patient_name = form_data.get("patient_name")
        patient_phone = form_data.get("patient_phone", "-")
        national_id = form_data.get("national_id", "-").strip()
        service_type = form_data.get("service_type")
        department = form_data.get("department")
        target_employee = form_data.get("target_employee", "-")
        send_whatsapp = form_data.get("send_whatsapp_flag", "yes")

        # منع تكرار رقم الهوية
        if national_id and national_id != "-":
            try:
                check_res = supabase.table("support_unit_records").select("id").eq("national_id", national_id).execute()
                if check_res.data and len(check_res.data) > 0:
                    return f"<script>alert('رقم الهوية ({national_id}) مسجل مسبقاً لمريض آخر ولا يمكن تكراره!'); window.history.back();</script>", 400
            except Exception as e:
                print("خطأ أثناء التحقق من رقم الهوية:", e)

        record = {
            "patient_name": patient_name,
            "patient_phone": patient_phone,
            "national_id": national_id,
            "file_number": form_data.get("file_number", "-"),
            "service_type": service_type,
            "department": department,
            "target_employee": target_employee,
            "notes": "-",
            "employee_name": logged_emp_name,
            "record_date": form_data.get("record_date"),
            "record_time": form_data.get("record_time")
        }
        try:
            supabase.table("support_unit_records").insert(record).execute()

            # إرسال التنبيه التلقائي للمريض عبر Green API عند اختيار الإرسال
            if send_whatsapp == "yes":
                send_whatsapp_green_api(
                    phone=patient_phone,
                    patient_name=patient_name,
                    service_type=service_type,
                    national_id=national_id,
                    department=department,
                    target_employee=target_employee,
                    logged_emp_name=logged_emp_name
                )

            return redirect(url_for("index"))
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    search_id = request.args.get("search_id", "").strip()
    from_date = request.args.get("from_date", "").strip()
    to_date = request.args.get("to_date", "").strip()

    try:
        query = supabase.table("support_unit_records").select("*")

        if search_id or from_date or to_date:
            if search_id:
                query = query.ilike("national_id", f"%{search_id}%")
            if from_date:
                query = query.gte("record_date", from_date)
            if to_date:
                query = query.lte("record_date", to_date)
        else:
            twelve_hours_ago = (datetime.now() - timedelta(hours=12)).strftime('%Y-%m-%d')
            query = query.gte("record_date", twelve_hours_ago)

        response = query.order("id", desc=True).execute()
        records = response.data or []
    except Exception as e:
        print("Error fetching records:", e)
        records = []

    return render_template(
        "index.html", 
        records=records, 
        logged_employee=session.get("employee_name"),
        can_edit=session.get("can_edit", True),
        user_role=session.get("role"),
        is_volunteer=(session.get("user") in VOLUNTEER_ACCOUNTS)
    )

@app.route("/update_action", methods=["POST"])
def update_action():
    """تحديث الإجراء المتخذ عند النقر على اسم المريض وتأكيد الحفظ"""
    if "user" not in session or not session.get("can_edit", True):
        return jsonify({"success": False, "message": "غير مصرح لك"}), 403

    data = request.get_json()
    record_id = data.get("record_id")
    action_taken = data.get("action_taken", "")

    try:
        supabase.table("support_unit_records").update({"notes": action_taken}).eq("id", record_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/export_excel")
def export_excel():
    if "user" not in session:
        return redirect(url_for("login"))

    try:
        response = supabase.table("support_unit_records").select("*").order("id", desc=True).execute()
        records = response.data or []

        if not records:
            return "لا توجد سجلات للتصدير", 400

        df = pd.DataFrame(records)
        
        rename_map = {
            "id": "#",
            "patient_name": "اسم المريض",
            "patient_phone": "رقم الجوال",
            "national_id": "رقم الهوية",
            "file_number": "رقم الملف",
            "service_type": "الخدمة المطلوبة",
            "department": "القسم",
            "target_employee": "الموظف المعني",
            "notes": "الاجراء المتخذ / الملاحظات",
            "employee_name": "موظف تجربة المريض",
            "record_date": "التاريخ",
            "record_time": "الوقت"
        }
        df = df.rename(columns=rename_map)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="السجلات")
        output.seek(0)

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
