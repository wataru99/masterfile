from flask import Blueprint, render_template, request, redirect, url_for, g
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
import sqlite3, os

user_bp = Blueprint('user', __name__)

# SQLite接続
def get_connection():
    if 'db' not in g:
        g.db = sqlite3.connect("instance/db.sqlite3")
        g.db.row_factory = sqlite3.Row
    return g.db

# マイページ表示
@user_bp.route("/dashboard/<int:user_id>")
def user_dashboard(user_id):
    conn = get_connection()

    user = conn.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return "ユーザーが見つかりません", 404

    dms = conn.execute("""
    SELECT dm.id, dm.message, dm.responded, dm.accepted, dm.chat_session_id,
           company.name AS company_name
    FROM dm
    JOIN company ON dm.company_id = company.id
    WHERE dm.user_id = ?
    ORDER BY dm.id DESC
""", (user_id,)).fetchall()


    return render_template("user_dashboard.html", user=user, dms=dms)

# DM削除
@user_bp.route("/dashboard/<int:user_id>/dm/<int:dm_id>/delete", methods=["POST"])
def delete_dm(user_id, dm_id):
    conn = get_connection()
    conn.execute("DELETE FROM dm WHERE id = ? AND user_id = ?", (dm_id, user_id))
    conn.commit()
    return redirect(url_for("user.user_dashboard", user_id=user_id))

# DM詳細・対応
@user_bp.route("/dashboard/<int:user_id>/dm/<int:dm_id>", methods=["GET", "POST"])
def dm_detail(user_id, dm_id):
    conn = get_connection()
    dm = conn.execute("""
        SELECT dm.*, company.name AS company_name
        FROM dm
        JOIN company ON dm.company_id = company.id
        WHERE dm.id = ? AND dm.user_id = ?
    """, (dm_id, user_id)).fetchone()

    if not dm:
        return "DMが見つかりませんでした", 404

    if request.method == "POST":
        response = request.form["response"]
        accepted = 1 if response == "accept" else 0
        responded = 1
        chat_session_id = None

        # ここでDBの更新を行う
        cur = conn.cursor()

        if accepted:
            cur.execute("""
                INSERT INTO chat_session (user_id, company_id, dm_id)
                VALUES (?, ?, ?)
            """, (dm["user_id"], dm["company_id"], dm["id"]))
            chat_session_id = cur.lastrowid

        cur.execute("""
            UPDATE dm SET responded = ?, accepted = ?, chat_session_id = ? WHERE id = ?
        """, (responded, accepted, chat_session_id, dm_id))
        conn.commit()

        if accepted and chat_session_id:
            return redirect(url_for("user.chat", session_id=chat_session_id))
        return redirect(url_for("user.user_dashboard", user_id=user_id))

    return render_template("dm_detail.html", dm=dm, user_id=user_id)



# チャット画面
@user_bp.route("/chat/<int:session_id>")
def chat(session_id):
    conn = get_connection()
    chat = conn.execute("SELECT * FROM chat_session WHERE id = ?", (session_id,)).fetchone()
    messages = conn.execute("SELECT * FROM message WHERE session_id = ? ORDER BY timestamp ASC", (session_id,)).fetchall()
    dm = conn.execute("""
        SELECT dm.*, company.id AS company_id, company.name AS company_name
        FROM dm
        JOIN company ON dm.company_id = company.id
        WHERE dm.chat_session_id = ?
    """, (session_id,)).fetchone()

    # ユーザー情報取得（オプション、名前・画像表示用などに使うなら）
    user = conn.execute("SELECT * FROM user WHERE id = ?", (dm["user_id"],)).fetchone() if dm else None

    return render_template("user_chat.html", session=chat, messages=messages, dm=dm, user=user)

# チャット削除
@user_bp.route("/chat/<int:session_id>/delete", methods=["POST"])
def delete_chat(session_id):
    conn = get_connection()
    dm = conn.execute("SELECT user_id FROM dm WHERE chat_session_id = ?", (session_id,)).fetchone()
    conn.execute("DELETE FROM chat_session WHERE id = ?", (session_id,))
    conn.commit()

    if dm:
        return redirect(url_for("user.user_dashboard", user_id=dm["user_id"]))
    return "削除後にユーザー情報が見つかりませんでした", 404


# プロフィール編集
@user_bp.route("/dashboard/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):
    conn = get_connection()
    cur = conn.cursor()

    user = cur.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return "ユーザーが見つかりませんでした", 404

    if request.method == "POST":
        full_name = request.form["full_name"]
        address = request.form["address"]
        phone_number = request.form["phone_number"]
        email = request.form["email"]
        current_occupation = request.form["current_occupation"]
        desired_conditions = request.form["desired_conditions"]

        # 画像処理
        photo_url = user["photo_url"]
        image_file = request.files.get("photo_url")
        if image_file and image_file.filename:
            photo_url = secure_filename(image_file.filename)
            image_file.save(os.path.join("static/uploads", photo_url))
        elif request.form.get("delete_image"):
            photo_url = None

        # パスワード変更処理
        new_password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if new_password or confirm_password:
            if new_password != confirm_password:
                return "パスワードが一致しません", 400
            password_hash = generate_password_hash(new_password)
        else:
            password_hash = user["password"]  # パスワード未変更

        cur.execute("""
            UPDATE user SET
                full_name = ?, address = ?, phone_number = ?, email = ?,
                current_occupation = ?, desired_conditions = ?, photo_url = ?, password = ?
            WHERE id = ?
        """, (full_name, address, phone_number, email,
              current_occupation, desired_conditions, photo_url, password_hash, user_id))
        conn.commit()

        return redirect(url_for("user.user_dashboard", user_id=user_id))

    return render_template("user_edit.html", user=user)