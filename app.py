from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB = "skillswap.db"

# ---------- DATABASE SETUP ----------
def init_db():
    if not os.path.exists(DB):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        # users: id, name, email, password, grade, can_teach, want_learn
        c.execute("""CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    email TEXT UNIQUE,
                    password TEXT,
                    grade TEXT,
                    can_teach TEXT,
                    want_learn TEXT
                    )""")
        # requests: id, from_id, to_id, skill, status
        c.execute("""CREATE TABLE requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_id INTEGER,
                    to_id INTEGER,
                    skill TEXT,
                    status TEXT
                    )""")
        # messages: id, sender_id, receiver_id, content
        c.execute("""CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER,
                    receiver_id INTEGER,
                    content TEXT
                    )""")
        conn.commit()
        conn.close()

init_db()

# ---------- DATABASE HELPERS ----------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return user

def get_user_by_email(email):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return user

def get_all_users(exclude_id=None):
    conn = get_db()
    if exclude_id:
        users = conn.execute("SELECT * FROM users WHERE id!=?", (exclude_id,)).fetchall()
    else:
        users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return users

def get_user_chats(user_id):
    conn = get_db()
    # get distinct user IDs the current user has chatted with
    rows = conn.execute("""
        SELECT DISTINCT u.id, u.name
        FROM messages m
        JOIN users u ON (u.id = m.sender_id OR u.id = m.receiver_id)
        WHERE u.id != ? AND (m.sender_id=? OR m.receiver_id=?)
    """, (user_id, user_id, user_id)).fetchall()
    conn.close()
    return rows

def get_matches(user_id):
    current_user = get_user(user_id)
    want_skills = [s.strip() for s in current_user["want_learn"].split(",")]
    matches = []
    all_users = get_all_users(user_id)
    conn = get_db()
    for u in all_users:
        teach_skills = [s.strip() for s in u["can_teach"].split(",")]
        for skill in want_skills:
            if skill in teach_skills:
                req = conn.execute("SELECT * FROM requests WHERE from_id=? AND to_id=? AND skill=?", 
                                   (user_id, u["id"], skill)).fetchone()
                matches.append({
                    "id": u["id"],
                    "name": u["name"],
                    "skill": skill,
                    "requested": bool(req)
                })
    conn.close()
    return matches

def get_requests(user_id):
    conn = get_db()
    reqs = conn.execute("""SELECT r.id, u.name, r.skill, r.status, r.from_id
                           FROM requests r
                           JOIN users u ON r.from_id = u.id
                           WHERE r.to_id=?""", (user_id,)).fetchall()
    conn.close()
    return reqs

def get_messages(user1, user2):
    conn = get_db()
    msgs = conn.execute("""SELECT u.name, m.content, m.sender_id
                           FROM messages m
                           JOIN users u ON u.id = m.sender_id
                           WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
                           ORDER BY m.id""", (user1, user2, user2, user1)).fetchall()
    conn.close()
    return msgs

# ---------- ROUTES ----------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "register":
            name = request.form.get("name")
            email = request.form.get("email")
            password = request.form.get("password")
            grade = request.form.get("grade")
            can_teach = request.form.get("can_teach")
            want_learn = request.form.get("want_learn")
            hashed_pw = generate_password_hash(password)
            conn = get_db()
            try:
                c = conn.cursor()
                c.execute("INSERT INTO users (name,email,password,grade,can_teach,want_learn) VALUES (?,?,?,?,?,?)",
                          (name,email,hashed_pw,grade,can_teach,want_learn))
                conn.commit()
                user_id = c.lastrowid
                conn.close()
                session["user_id"] = user_id
                return redirect("/dashboard")
            except sqlite3.IntegrityError:
                conn.close()
                return "Email already registered!"
        elif action == "login":
            email = request.form.get("email")
            password = request.form.get("password")
            user = get_user_by_email(email)
            if user and check_password_hash(user["password"], password):
                session["user_id"] = user["id"]
                return redirect("/dashboard")
            else:
                return "Invalid email or password!"
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")
    user = get_user(session["user_id"])
    return render_template("dashboard.html", user=user, active_page="dashboard")

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/")
    user = get_user(session["user_id"])
    return render_template("profile.html", user=user, active_page="profile")

@app.route("/matching")
def matching():
    if "user_id" not in session:
        return redirect("/")
    user = get_user(session["user_id"])
    matches = get_matches(user["id"])
    return render_template("matching.html", user=user, matches=matches, active_page="matching")

@app.route("/requests")
def requests_page():
    if "user_id" not in session:
        return redirect("/")
    user = get_user(session["user_id"])
    reqs = get_requests(user["id"])
    return render_template("requests.html", user=user, requests=reqs, active_page="requests")

@app.route("/chatlist")
def chatlist():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/")

    chats = get_user_chats(user_id)  # all users you chatted with
    return render_template("chatlist.html", chats=chats, other=None, messages=None, current=user_id, active_page="chatlist")

@app.route("/send_request/<int:to_id>/<skill>")
def send_request(to_id, skill):
    user_id = session.get("user_id")
    if not user_id: return redirect("/")
    conn = get_db()
    conn.execute("INSERT INTO requests (from_id,to_id,skill,status) VALUES (?,?,?,?)",
                 (user_id,to_id,skill,"pending"))
    conn.commit()
    conn.close()
    return redirect("/matching")

@app.route("/accept/<int:req_id>")
def accept(req_id):
    user_id = session.get("user_id")
    if not user_id: return redirect("/")
    conn = get_db()
    conn.execute("UPDATE requests SET status='accepted' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()
    return redirect("/requests")

@app.route("/chatlist/<int:other_id>", methods=["GET","POST"])
def chat(other_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/")

    if request.method == "POST":
        msg = request.form.get("message")
        if msg:
            conn = get_db()
            conn.execute(
                "INSERT INTO messages (sender_id, receiver_id, content) VALUES (?,?,?)",
                (user_id, other_id, msg)
            )
            conn.commit()
            conn.close()
            return redirect(f"/chatlist/{other_id}") 

    other = get_user(other_id)
    messages = get_messages(user_id, other_id)
    chats = get_user_chats(user_id)
    current = user_id
    return render_template(
        "chatlist.html",
        chats=chats,
        other=other,
        messages=messages,
        current=current,
        active_page="chatlist"
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__=="__main__":
    app.run(debug=True)