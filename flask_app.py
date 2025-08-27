from flask import Flask, redirect, render_template, request, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
import pytz

app = Flask(__name__)
app.config["DEBUG"] = True

SQLALCHEMY_DATABASE_URI = (
    "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
        username="Sharonj",
        password="kolopis123",
        hostname="Sharonj.mysql.pythonanywhere-services.com",
        databasename="Sharonj$comments",
    )
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

app.secret_key = "something only you know"
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ✅ SQLAlchemy User model
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(4096))
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    author = db.Column(db.String(80), nullable=False, default="anonymous")


# ✅ Create tables & default users if not already present
with app.app_context():
    db.create_all()
    default_users = [
        ("admin", "secret"),
        ("bob", "less-secret"),
        ("caroline", "completelysecret"),
        ("tester", "super-secret"),
    ]
    for username, pwd in default_users:
        if not User.query.filter_by(username=username).first():
            db.session.add(User(username=username, password_hash=generate_password_hash(pwd)))
    db.session.commit()


SGT = pytz.timezone("Asia/Singapore")


@app.route("/", methods=["GET"])
def index():
    comments = Comment.query.order_by(Comment.timestamp.desc()).all()
    for c in comments:
        c.local_time = c.timestamp.replace(tzinfo=pytz.utc).astimezone(SGT)
    return render_template("main_page.html", comments=comments)


@app.route("/intro")
def intro():
    return render_template("intro_page.html", datetime=datetime)

@app.context_processor
def inject_datetime():
    # makes `datetime` usable in any template: {{ datetime.utcnow().year }}
    return {"datetime": datetime}

@app.route("/add_comment", methods=["POST"])
@login_required
def add_comment():
    text = request.form.get("contents", "").strip()
    if not text:
        return redirect(url_for("index"))

    new_comment = Comment(
        content=text,
        author=current_user.username,  # store username from DB
        timestamp=datetime.utcnow(),
    )
    db.session.add(new_comment)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login_page.html", error=False)

    username = request.form["username"].strip()
    password = request.form["password"]

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return render_template("login_page.html", error=True)

    login_user(user)
    return redirect(url_for("index"))


@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))
