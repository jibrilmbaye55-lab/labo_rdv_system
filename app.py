import sqlite3
from flask import Flask, render_template, request, redirect, send_file, session
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# =========================
# INITIALISATION APP
# =========================
app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = 'static/uploads'
PDF_FOLDER = 'static/pdfs'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PDF_FOLDER'] = PDF_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

# =========================
# DATABASE
# =========================
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rendezvous (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_patient TEXT,
        nom TEXT,
        prenom TEXT,
        adresse TEXT,
        telephone TEXT,
        matricule TEXT,
        bulletin TEXT,
        date_rdv TEXT,
        heure_rdv TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reclamations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        telephone TEXT,
        type_reclamation TEXT,
        priorite TEXT,
        message TEXT,
        date TEXT,
        statut TEXT DEFAULT 'En attente'
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# PDF AVEC NUMERO 🔥
# =========================
def generate_pdf(nom, prenom, date, heure, numero_ticket):
    filename = f"ticket_{nom}_{int(datetime.now().timestamp())}.pdf"
    filepath = os.path.join(app.config['PDF_FOLDER'], filename)

    doc = SimpleDocTemplate(filepath)
    styles = getSampleStyleSheet()
    elements = []

    logo_path = "static/logo_labo.png"
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=80, height=50))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>LABORATOIRE MEDICAL COUD</b>", styles['Title']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"<b>Numéro : {numero_ticket}</b>", styles['Normal']))
    elements.append(Spacer(1, 15))

    data = [
        ["Nom", f"{nom} {prenom}"],
        ["Date", date],
        ["Heure", heure],
    ]

    table = Table(data, colWidths=[100, 250])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.lightblue),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))

    elements.append(table)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Merci de vous presenter a l'heure.", styles['Normal']))

    doc.build(elements)

    return filename

# =========================
# LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == "admin" and request.form.get('password') == "1234":
            session['admin'] = True
            return redirect('/admin')
        else:
            return "❌ Mauvais identifiants"
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# =========================
# ACCUEIL
# =========================
@app.route('/')
def index():
    return render_template('index.html')

# =========================
# RDV INTELLIGENT 🔥🔥🔥
# =========================
@app.route('/rdv', methods=['GET', 'POST'])
def rdv():
    if request.method == 'POST':

        type_patient = request.form.get('type_patient')
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        adresse = request.form.get('adresse')
        telephone = request.form.get('telephone')
        matricule = request.form.get('matricule')

        if type_patient in ["Etudiant", "Personnel COUD"] and not matricule:
            return "❌ Matricule obligatoire"

        file = request.files.get('bulletin')
        if not file:
            return "❌ Bulletin obligatoire"

        filename = secure_filename(file.filename)
        unique_name = f"{int(datetime.now().timestamp())}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # 🔥 JOUR SUIVANT
        date_rdv = datetime.now() + timedelta(days=1)

        # 🔥 PAS WEEKEND
        while date_rdv.weekday() >= 5:
            date_rdv += timedelta(days=1)

        # 🔥 TROUVER JOUR DISPONIBLE
        while True:
            date_str = date_rdv.strftime("%Y-%m-%d")

            cursor.execute("SELECT COUNT(*) FROM rendezvous WHERE date_rdv=?", (date_str,))
            count = cursor.fetchone()[0]

            if count < 100:
                break
            else:
                date_rdv += timedelta(days=1)
                while date_rdv.weekday() >= 5:
                    date_rdv += timedelta(days=1)

        # 🔥 HEURE ENTRE 08H - 11H
        start_time = datetime.strptime("08:00", "%H:%M")
        rdv_time = start_time + timedelta(minutes=2 * count)
        heure = rdv_time.strftime("%H:%M")

        # 🔥 NUMERO UNIQUE
        numero_ticket = f"RDV-{date_str.replace('-', '')}-{str(count+1).zfill(3)}"

        cursor.execute("""
        INSERT INTO rendezvous 
        (type_patient, nom, prenom, adresse, telephone, matricule, bulletin, date_rdv, heure_rdv)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (type_patient, nom, prenom, adresse, telephone, matricule, unique_name, date_str, heure))

        conn.commit()
        conn.close()

        pdf = generate_pdf(nom, prenom, date_str, heure, numero_ticket)

        return render_template(
            "confirmation.html",
            nom=nom,
            prenom=prenom,
            date=date_str,
            heure=heure,
            numero=numero_ticket,
            pdf=pdf
        )

    return render_template('rdv.html')

# =========================
# DOWNLOAD PDF
# =========================
@app.route('/download/<filename>')
def download(filename):
    return send_file(os.path.join(app.config['PDF_FOLDER'], filename), as_attachment=True)

# =========================
# RECLAMATIONS
# =========================
@app.route('/reclamation', methods=['GET', 'POST'])
def reclamation():
    if request.method == 'POST':
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO reclamations (nom, telephone, type_reclamation, priorite, message, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request.form.get('nom'),
            request.form.get('telephone'),
            request.form.get('type_reclamation'),
            request.form.get('priorite'),
            request.form.get('message'),
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        conn.commit()
        conn.close()

        return render_template("confirmation_reclamation.html", nom=request.form.get('nom'))

    return render_template('reclamation.html')

# =========================
# ADMIN
# =========================
@app.route('/admin')
def admin():

    if not session.get('admin'):
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM rendezvous ORDER BY date_rdv DESC, heure_rdv ASC")
    rdvs = cursor.fetchall()

    cursor.execute("""
    SELECT * FROM reclamations
    ORDER BY 
        priorite='Urgent' DESC,
        statut='En attente' DESC,
        date DESC
    """)
    reclamations = cursor.fetchall()

    conn.close()

    return render_template("admin.html", rdvs=rdvs, reclamations=reclamations)

# =========================
# ACTIONS
# =========================
@app.route('/traiter_reclamation/<int:id>')
def traiter_reclamation(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE reclamations SET statut='Traité' WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/admin')

@app.route('/delete_rdv/<int:id>')
def delete_rdv(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM rendezvous WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/admin')

@app.route('/delete_reclamation/<int:id>')
def delete_reclamation(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM reclamations WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/admin')

# =========================
# RUN
# =========================
if __name__ == '__main__':
    app.run(debug=True)