from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    email = db.Column(db.String(128))

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))

class DM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded = db.Column(db.Boolean, default=False)
    accepted = db.Column(db.Boolean, default=None)  # True: OK / False: 拒否 / None: 未応答

    # リレーション追加（これが重要）
    chat_session = db.relationship('ChatSession', backref='dm', uselist=False)
    company = db.relationship('Company')  # DM側から企業名を取得したいため

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dm_id = db.Column(db.Integer, db.ForeignKey('dm.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'))
    sender_type = db.Column(db.String(10))  # 'user' or 'company'
    sender_id = db.Column(db.Integer)       # user.id or company.id
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
