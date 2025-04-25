from flask import Blueprint, render_template, g, request, redirect, url_for
from datetime import datetime
import sqlite3
import random

company_bp = Blueprint('company', __name__)

def generate_random_id(length=12):
    return ''.join(random.choices("0123456789", k=length))

def get_connection():
    if 'db' not in g:
        g.db = sqlite3.connect("instance/db.sqlite3")
        g.db.row_factory = sqlite3.Row
    return g.db

@company_bp.route("/<company_code>/candidates")
def candidates(company_code):
    conn = get_connection()
    users = conn.execute("SELECT * FROM user").fetchall()
    return render_template("candidates.html", users=users, company_code=company_code)

@company_bp.route("/<company_code>/candidates/<int:user_id>")
def candidates_detail(company_code, user_id):
    conn = get_connection()
    cur = conn.cursor()

    user = cur.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return "ユーザーが見つかりません", 404

    company = cur.execute("SELECT * FROM company WHERE code = ?", (company_code,)).fetchone()
    if not company:
        return "企業が見つかりません", 404

    dm = cur.execute("""
        SELECT * FROM dm WHERE user_id = ? AND company_id = ?
    """, (user_id, company["id"])).fetchone()

    has_applied = dm is not None

    return render_template("candidates_detail.html", user=user, company_code=company_code, has_applied=has_applied)

@company_bp.route("/company/<company_code>/dm/<int:user_id>", methods=["GET", "POST"])
def dm_form(company_code, user_id):
    conn = get_connection()
    cur = conn.cursor()

    company = cur.execute("SELECT * FROM company WHERE code = ?", (company_code,)).fetchone()
    user = cur.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()

    if request.method == "POST":
        message = request.form["message"]
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dm_id = generate_random_id()

        cur.execute("""
            INSERT INTO dm (id, company_id, user_id, message, created_at, responded, accepted, chat_session_id)
            VALUES (?, ?, ?, ?, ?, 0, 0, NULL)
        """, (dm_id, company["id"], user_id, message, created_at))
        conn.commit()

        return render_template("dm_sent.html", company_code=company_code)

    return render_template("dm_form.html", user=user, company_code=company_code)

@company_bp.route("/<company_code>/matched_dms", endpoint="company_matched_dms")
def matched_dms(company_code):
    conn = get_connection()
    cur = conn.cursor()

    company = cur.execute("SELECT * FROM company WHERE code = ?", (company_code,)).fetchone()
    if not company:
        return "企業が見つかりません", 404

    company_id = company["id"]

    rows = cur.execute("""
        SELECT dm.*, user.full_name, user.photo_url, user.current_occupation, user.address,
               user.membership, user.featured, chat_session.id AS chat_session_id
        FROM dm
        JOIN user ON dm.user_id = user.id
        LEFT JOIN chat_session ON dm.id = chat_session.dm_id
        WHERE dm.company_id = ? AND dm.accepted = 1
    """, (company_id,)).fetchall()

    unique_users = {}
    for row in rows:
        user_id = row["user_id"]
        if user_id not in unique_users:
            unique_users[user_id] = row

    return render_template("matched_dms.html", users=list(unique_users.values()), company_code=company_code)

@company_bp.route("/chat/<int:session_id>")
def company_chat(session_id):
    conn = get_connection()
    chat = conn.execute("SELECT * FROM chat_session WHERE id = ?", (session_id,)).fetchone()
    messages = conn.execute("SELECT * FROM message WHERE session_id = ? ORDER BY timestamp ASC", (session_id,)).fetchall()
    dm = conn.execute("""
    SELECT dm.*, 
           user.full_name AS user_name, 
           user.photo_url AS user_photo_url,
           company.name AS company_name, 
           company.id AS company_id,
           company.logo_url AS company_logo_url
    FROM dm
    JOIN user ON dm.user_id = user.id
    JOIN company ON dm.company_id = company.id
    WHERE dm.chat_session_id = ?
""", (session_id,)).fetchone()
    
    return render_template("company_chat.html", session=chat, messages=messages, dm=dm)

