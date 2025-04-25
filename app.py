import eventlet
eventlet.monkey_patch()  # SocketIOには必須！

import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from datetime import datetime
from models import User
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO




# === Flask基本設定 ===
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MBまで
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DB_PATH = os.path.join(basedir, 'instance', 'db.sqlite3')

# === SocketIO 初期化 ===
socketio = SocketIO(app, cors_allowed_origins="*")
# === SQLite 接続関数 ===
def get_connection():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route("/dashboard")
def dashboard():
    conn = get_connection()
    cur = conn.cursor()
    achievement_users = cur.execute("SELECT * FROM user WHERE achievement = 1").fetchall()
    top_users = cur.execute("SELECT * FROM user ORDER BY point DESC LIMIT 5").fetchall()
    return render_template("dashboard.html", achievement_users=achievement_users, top_users=top_users)


@app.route("/detail/<int:user_id>")
def candidates_detail(user_id):
    conn = get_connection()
    cur = conn.cursor()
    user = cur.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    return render_template("candidates_detail.html", user=user, company_code=None)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()
        user = cur.execute("""
            SELECT * FROM user WHERE id = ? OR email = ?
        """, (username, username)).fetchone()

        if user and check_password_hash(user["password"], password):
            return redirect(url_for("user.user_dashboard", user_id=user["id"]))
        else:
            return "ログインに失敗しました", 401

    return render_template("user_login.html")


@app.route("/")
def index():
    conn = get_connection()
    cur = conn.cursor()

    sort = request.args.get("sort", "point")
    membership = request.args.get("membership", "")
    featured = request.args.get("featured", "")
    q = request.args.get("q", "")

    sql = "SELECT * FROM user WHERE 1=1"
    params = []

    if membership:
        sql += " AND membership = ?"
        params.append(membership)
    if featured == "1":
        sql += " AND featured = 1"
    if q:
        sql += " AND (full_name LIKE ? OR current_occupation LIKE ? OR address LIKE ?)"
        params.extend([f"%{q}%"] * 3)

    sql += " ORDER BY " + ("point DESC" if sort == "point" else "id DESC")

    users = cur.execute(sql, params).fetchall()
    return render_template("index.html", users=users, sort=sort, membership=membership, featured=featured, q=q)


@app.route("/edit/<int:user_id>", methods=["GET", "POST"])
def edit(user_id):
    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        full_name = request.form["full_name"]
        gender = request.form.get("gender", "")
        age = request.form["age"]
        address = request.form["address"]
        phone_number = request.form["phone_number"]
        email = request.form["email"]
        current_occupation = request.form["current_occupation"]
        desired_conditions = request.form["desired_conditions"]
        intro = request.form["intro"]
        point = int(request.form.get("point", 0))
        membership = request.form.get("membership", "")
        achievement = 1 if request.form.get("achievement") == "1" else 0
        featured = 1 if request.form.get("featured") == "1" else 0

        # 現在の画像を取得
        current_user = cur.execute("SELECT photo_url FROM user WHERE id = ?", (user_id,)).fetchone()
        current_photo = current_user["photo_url"] if current_user else None

        # 画像処理
        image_file = request.files.get("photo_url")
        photo_url = current_photo  # デフォルトは現状維持

        if image_file and image_file.filename:
            # 新しい画像に差し替え
            photo_url = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_url))
        elif request.form.get("delete_image"):
            # 古い画像を削除
            if current_photo:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], current_photo))
                except FileNotFoundError:
                    pass
            photo_url = None

        # UPDATE クエリ実行
        cur.execute("""
            UPDATE user SET full_name=?, gender=?, age=?, address=?, phone_number=?,
            email=?, current_occupation=?, desired_conditions=?, intro=?, point=?,
            membership=?, achievement=?, featured=?, photo_url=?
            WHERE id=?
        """, (
            full_name, gender, age, address, phone_number,
            email, current_occupation, desired_conditions, intro, point,
            membership, achievement, featured, photo_url, user_id
        ))
        conn.commit()
        return redirect(url_for("index"))

    user = cur.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    return render_template("edit.html", user=user)



import random

def generate_random_id(length=16):
    return ''.join(random.choices("0123456789", k=length))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_id = generate_random_id(16)

        full_name = request.form["full_name"]
        gender = request.form.get("gender", "")
        age = request.form["age"]
        address = request.form["address"]
        phone_number = request.form["phone_number"]
        email = request.form["email"]
        current_occupation = request.form["current_occupation"]
        desired_conditions = request.form["desired_conditions"]
        intro = request.form["intro"]
        point = int(request.form.get("point", 0))

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "パスワードが一致しません", 400

        password_hash = generate_password_hash(password)

        # 画像ファイル処理
        photo_url = None
        image_file = request.files.get("photo_url")
        if image_file and image_file.filename:
            photo_url = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_url))

        # データベース挿入処理
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user (
                id, full_name, gender, age, address, phone_number, email,
                current_occupation, desired_conditions, intro, point,
                photo_url, membership, achievement, featured, password
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', 0, 0, ?)
        """, (
            user_id, full_name, gender, age, address, phone_number, email,
            current_occupation, desired_conditions, intro, point,
            photo_url, password_hash
        ))
        conn.commit()

        return render_template("register_user.html", user_id=user_id)

    return render_template("register.html")

from werkzeug.security import check_password_hash




# === SocketIOイベント（チャット送信） ===
@socketio.on('send_message')
def handle_send_message(data):
    message = data.get('message', '').strip()
    sender_type = data.get('sender_type')
    sender_id = data.get('sender_id')
    session_id = data.get('session_id')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not all([message, sender_type, sender_id, session_id]):
        return  # 入力不備がある場合は無視

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    sender_name = "不明"
    photo_url = "default.jpg"

    try:
        if sender_type == 'company':
            sender = conn.execute("SELECT name FROM company WHERE id = ?", (sender_id,)).fetchone()
            if sender:
                sender_name = sender["name"]
            photo_url = "default_company.png"
        elif sender_type == 'user':
            sender = conn.execute("SELECT full_name, photo_url FROM user WHERE id = ?", (sender_id,)).fetchone()
            if sender:
                sender_name = sender["full_name"]
                photo_url = sender["photo_url"] or "default.jpg"

        # メッセージ保存
        conn.execute("""
            INSERT INTO message (session_id, sender_type, sender_id, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, sender_type, sender_id, message, timestamp))
        conn.commit()

        # メッセージ送信
        emit('receive_message', {
            'message': message,
            'sender_type': sender_type,
            'sender_id': sender_id,
            'sender_name': sender_name,
            'photo_url': photo_url,
            'timestamp': timestamp
        }, broadcast=True)
    finally:
        conn.close()




extra_pages = [
    'achievements', 'ai_diagnosis', 'application_status',
    'blocked_users', 'company', 'company_detail', 'contact', 'contact_complete', 'contact_detail', 'contact_list',
    'contact_reply', 'faq', 'favorites', 'former_pr', 'job_applicants', 'job_application_detail', 'job_listings',
    'job_posting', 'job_search_results', 'job_seekers', 'media_coverage', 'message_history',
    'narrator', 'notification_settings', 'password_reset_complete', 'pricing', 'privacy', 'profile_edit',
    'profile_visibility', 'scout', 'scout_complete', 'scout_form', 'sitemap', 'stage_actor', 'system_settings',
    'takara', 'terms', 'user_notifications', 'withdraw_complete', 'withdrawal_confirm',
    'admin_dashboard', 'announcer', 'athlete', 'comedian'
    # 'ai_diagnosis_result' はすでに個別定義しているため除外
]

for page in extra_pages:
    route_path = f"/{page.replace('_', '-')}"
    template_file = f"{page}.html"
    app.add_url_rule(route_path, page, lambda p=template_file: render_template(p))


# === SQLAlchemy/Blueprint統合（元・1つ目サイト） ===
from flask_sqlalchemy import SQLAlchemy
from models import db
from user_routes import user_bp
from company_routes import company_bp
from admin_routes import admin_bp

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

with app.app_context():
    db.init_app(app)

app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(company_bp, url_prefix="/company")
app.register_blueprint(admin_bp, url_prefix="/admin")

# Flask起動 → SocketIO起動に変更
if __name__ == "__main__":
    socketio.run(app, debug=True)
