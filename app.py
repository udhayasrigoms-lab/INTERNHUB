from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE = "database.db"

# ---------------- DATABASE CONNECTION ----------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- DATABASE INITIALIZATION ----------------
def init_db():
    conn = get_db()

    # USERS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    # INTERNSHIPS TABLE (UNIQUE company + domain)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS internships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            domain TEXT,
            slots INTEGER,
            UNIQUE(company_name, domain)
        )
    """)

    # APPLICATIONS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            email TEXT,
            company_name TEXT,
            domain TEXT,
            applied_at TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= SIGNUP =================
@app.route("/signup", methods=["POST", "OPTIONS"])
def signup():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200

    data = request.json
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO users (first_name, last_name, email, password) VALUES (?,?,?,?)",
            (data["firstName"], data["lastName"], data["email"], data["password"])
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Signup successful"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "User already exists"}), 400

# ================= LOGIN =================
@app.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200

    data = request.json
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (data["email"], data["password"])
    ).fetchone()

    conn.close()

    if user:
        return jsonify({
            "message": "Login successful",
            "user": {
                "firstName": user["first_name"],
                "lastName": user["last_name"],
                "email": user["email"]
            }
        })
    else:
        return jsonify({"error": "Invalid credentials"}), 401

# ================= GET INTERNSHIPS =================
@app.route("/internships", methods=["GET"])
def get_internships():
    conn = get_db()
    data = conn.execute("SELECT * FROM internships").fetchall()
    conn.close()
    return jsonify([dict(i) for i in data])

# ================= ADD / UPDATE INTERNSHIP =================
@app.route("/add-internship", methods=["POST"])
def add_or_update_internship():
    data = request.json
    conn = get_db()

    # Insert if new, update if exists
    conn.execute("""
        INSERT INTO internships (company_name, domain, slots)
        VALUES (?, ?, ?)
        ON CONFLICT(company_name, domain)
        DO UPDATE SET slots=excluded.slots
    """, (data["company"], data["domain"], data["slots"]))

    conn.commit()
    conn.close()

    return jsonify({"message": "Internship added / updated successfully"})

# ================= APPLY FOR INTERNSHIP =================
@app.route("/apply", methods=["POST"])
def apply_internship():
    data = request.json
    conn = get_db()

    internship = conn.execute(
        "SELECT slots FROM internships WHERE company_name=? AND domain=?",
        (data["company"], data["domain"])
    ).fetchone()

    if not internship:
        conn.close()
        return jsonify({"error": "Internship not found"}), 404

    if internship["slots"] <= 0:
        conn.close()
        return jsonify({"error": "No slots available"}), 400

    # Reduce slot
    conn.execute(
        "UPDATE internships SET slots = slots - 1 WHERE company_name=? AND domain=?",
        (data["company"], data["domain"])
    )

    # Save application
    conn.execute("""
        INSERT INTO applications 
        (student_name, email, company_name, domain, applied_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data["student_name"],
        data["email"],
        data["company"],
        data["domain"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Application submitted successfully"})

# ================= VIEW APPLICATIONS =================
@app.route("/applications", methods=["GET"])
def view_applications():
    conn = get_db()
    data = conn.execute("SELECT * FROM applications").fetchall()
    conn.close()
    return jsonify([dict(a) for a in data])

# ================= RUN SERVER =================
if __name__ == "__main__":
    app.run(debug=True)
