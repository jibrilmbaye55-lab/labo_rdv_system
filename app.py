from flask import Flask, render_template, request, redirect, session, send_from_directory, send_file
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

# 🔥 PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "secret123"

DB_NAME = "database.db"

UPLOAD_FOLDER = "uploads"
PDF_FOLDER = "pdfs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

# =========================
# 🔌 CONNEXION DB
# =========================
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# =========================
# 🧱 INIT DB (AVEC HEURE)
# =========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rendezvous (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        prenom TEXT,
        type_patient TEXT,
        adresse TEXT,
        telephone TEXT,
        matricule TEXT,
        date_rdv TEXT,
        numero_ordre INTEGER,
        bulletin TEXT,
        date_creation TEXT
    )
    """)

    try:
        cursor.execute("ALTER TABLE rendezvous ADD COLUMN heure TEXT")
    except:
        pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reclamations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        telephone TEXT,
        message TEXT,
        urgence TEXT,
        service TEXT,
        date_creation TEXT
    )
    """)

    conn.commit()
    conn.close()

# =========================
# 🏠 HOME
# =========================
@app.route("/")
def home():
    return redirect("/labo")

@app.route("/labo")
def labo_home():
    return render_template("labo_home.html")

# =========================
# 🧪 RECLAMATION
# =========================
@app.route("/reclamation")
def reclamation():
    return render_template("form_labo.html")

@app.route("/submit_reclamation", methods=["POST"])
def submit_reclamation():

    if not request.form.get("telephone") or not request.form.get("message"):
        return "❌ Téléphone et message obligatoires"

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reclamations
    (nom, telephone, message, urgence, service, date_creation)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        request.form.get("nom"),
        request.form.get("telephone"),
        request.form.get("message"),
        request.form.get("urgence"),
        request.form.get("service"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return "✅ Réclamation envoyée avec succès"

# =========================
# 📅 RENDEZ-VOUS
# =========================
@app.route("/rendezvous")
def rendezvous():
    return render_template("rendezvous.html")

@app.route("/submit_rdv", methods=["POST"])
def submit_rdv():

    data = request.form

    if not all([data.get("nom"), data.get("prenom"), data.get("type_patient"),
                data.get("adresse"), data.get("telephone")]):
        return "❌ Tous les champs sont obligatoires"

    file = request.files.get("bulletin")

    if not file or file.filename == "":
        return "❌ Bulletin obligatoire"

    filename = secure_filename(file.filename)
    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(filepath)

    conn = get_db_connection()
    cursor = conn.cursor()

    slots = []
    for h in range(8, 11):
        for m in [0, 15, 30, 45]:
            slots.append(f"{h:02d}:{m:02d}")

    date_rdv = datetime.now().date()

    while True:
        for slot in slots:
            cursor.execute("""
            SELECT COUNT(*) as total FROM rendezvous
            WHERE date_rdv=? AND heure=?
            """, (str(date_rdv), slot))

            if cursor.fetchone()["total"] == 0:
                heure_rdv = slot
                break
        else:
            date_rdv += timedelta(days=1)
            continue
        break

    cursor.execute("""
    INSERT INTO rendezvous
    (nom, prenom, type_patient, adresse, telephone, matricule,
     date_rdv, heure, numero_ordre, bulletin, date_creation)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("nom"),
        data.get("prenom"),
        data.get("type_patient"),
        data.get("adresse"),
        data.get("telephone"),
        data.get("matricule"),
        str(date_rdv),
        heure_rdv,
        1,
        unique_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return f"✅ RDV le {date_rdv} à {heure_rdv}"

# =========================
# 📄 PDF
# =========================
@app.route("/rdv_pdf/<int:id>")
def rdv_pdf(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM rendezvous WHERE id=?", (id,))
    r = cursor.fetchone()
    conn.close()

    if not r:
        return "❌ RDV introuvable"

    filepath = os.path.join(PDF_FOLDER, f"rdv_{id}.pdf")

    doc = SimpleDocTemplate(filepath)
    styles = getSampleStyleSheet()

    content = [
        Paragraph("<b>RENDEZ-VOUS LABORATOIRE</b>", styles["Title"]),
        Paragraph(f"Nom: {r['nom']}", styles["Normal"]),
        Paragraph(f"Prénom: {r['prenom']}", styles["Normal"]),
        Paragraph(f"Téléphone: {r['telephone']}", styles["Normal"]),
        Paragraph(f"Date: {r['date_rdv']} à {r['heure']}", styles["Normal"]),
    ]

    doc.build(content)

    return send_file(filepath, as_attachment=True)

# =========================
# 📊 DASHBOARD RDV
# =========================
@app.route("/admin_rdv")
def admin_rdv():

    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM rendezvous
    ORDER BY date_rdv ASC, heure ASC
    """)

    rdv = cursor.fetchall()
    conn.close()

    return render_template("admin_rdv.html", rdv=rdv)

# =========================
# 🧑‍⚕️ STAFF
# =========================
@app.route("/staff")
def staff():

    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    today = datetime.now().date()

    cursor.execute("""
    SELECT * FROM rendezvous
    WHERE date_rdv=?
    ORDER BY heure ASC
    """, (str(today),))

    data = cursor.fetchall()
    conn.close()

    return render_template("staff.html", data=data)

# =========================
# ❌ DELETE
# =========================
@app.route("/delete_rdv/<int:id>")
def delete_rdv(id):

    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT bulletin FROM rendezvous WHERE id=?", (id,))
    row = cursor.fetchone()

    if row and row["bulletin"]:
        filepath = os.path.join(UPLOAD_FOLDER, row["bulletin"])
        if os.path.exists(filepath):
            os.remove(filepath)

    cursor.execute("DELETE FROM rendezvous WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin_rdv")

# =========================
# 📂 FILES
# =========================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# =========================
# 🔐 LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == "admin" and request.form.get("password") == "1234":
            session["logged_in"] = True
            return redirect("/admin_labo")

    return render_template("login.html")

# =========================
# 📊 LABO
# =========================
@app.route("/admin_labo")
def admin_labo():

    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reclamations WHERE service='Laboratoire' ORDER BY id DESC")
    reclamations = cursor.fetchall()

    conn.close()

    return render_template("admin_labo.html", reclamations=reclamations)

# =========================
# 🚪 LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# =========================
# 🚀 RUN (🔥 IMPORTANT)
# =========================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)