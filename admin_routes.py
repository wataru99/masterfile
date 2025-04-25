# admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session
from models import db, User, Company, DM, ChatSession, ChatMessage


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 管理者ログイン情報（簡易）
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"

def is_logged_in():
    return session.get('admin_logged_in')

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        return "ログイン失敗"
    return render_template('admin_login.html')

@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('admin.login'))
    return render_template('admin_dashboard.html')

@admin_bp.route('/users')
def users():
    dummy_users = [
        {'id': 1, 'name': '田中 太郎', 'email': 'taro@example.com'},
        {'id': 2, 'name': '佐藤 花子', 'email': 'hanako@example.com'},
        {'id': 3, 'name': '鈴木 次郎', 'email': 'jiro@example.com'},
        {'id': 4, 'name': '山田 三郎', 'email': 'saburo@example.com'},
        {'id': 5, 'name': '高橋 四郎', 'email': 'shiro@example.com'},
    ]
    return render_template('admin_users.html', users=dummy_users)


@admin_bp.route('/companies')
def companies():
    dummy_companies = [
        {'id': 1, 'name': '株式会社あいうえお'},
        {'id': 2, 'name': 'XYZ合同会社'},
        {'id': 3, 'name': 'TechTech Inc.'},
        {'id': 4, 'name': '未来企画'},
        {'id': 5, 'name': '株式会社グリーン'},
    ]
    return render_template('admin_companies.html', companies=dummy_companies)


@admin_bp.route('/dms')
def dms():
    if not is_logged_in():
        return redirect(url_for('admin.login'))
    dms = DirectMessage.query.all()
    return render_template('admin_dms.html', dms=dms)

@admin_bp.route('/chats')
def chats():
    if not is_logged_in():
        return redirect(url_for('admin.login'))
    chats = ChatSession.query.all()
    return render_template('admin_chats.html', chats=chats)

