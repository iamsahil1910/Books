import os

from flask import Flask, session, render_template, redirect, request, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash


from helpers import login_required

app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():

    user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()
    if len(user) != 0:
        return render_template("index.html", user = user)
    else:
        return redirect("/login")


@app.route("/login", methods=['GET', 'POST'])
def login():

    session.clear()

    if request.method == "GET":

        return render_template("login.html")

    else:

        if not request.form.get("username"):
            return render_template("login.html", message = "Username Missing")
        if not request.form.get("password"):
            return render_template("login.html", message = "Password Missing")

        row = db.execute("SELECT * FROM users WHERE username = :username", {'username': request.form.get("username")}).fetchall()

        if len(row) != 1 or not check_password_hash(row[0]["password"], request.form.get("password")):
            return render_template("login.html", message = "Username or Password is Incorrect!")

        session["user_id"] = row[0]["user_id"]

        return redirect("/")

@app.route("/register", methods=['GET', 'POST'])
def register():

    session.clear()

    if request.method == "POST":

        if not request.form.get("firstname"):
            return render_template("register.html", message = "FirstName Missing")

        if not request.form.get("lastname"):
            return render_template("register.html", message="LastName Missing")

        if not request.form.get("username"):
            return render_template("register.html", message = "Username Missing")

        if not request.form.get("password"):
            return render_template("register.html", message="Password Missing")

        if request.form.get("password") !=  request.form.get("confirmation"):
            return render_template("register.html", message="Password do not match")

        row = db.execute("SELECT * FROM users WHERE username = :username", {'username': request.form.get("username")}).fetchall()

        if len(row) != 0:
            return render_template("register.html", message = "Username Already Exist")

        else:
            key = db.execute("INSERT INTO users (firstname, lastname, username, password) VALUES(:firstname, :lastname, :username, :password)",
                  {'firstname': request.form.get("firstname"), 'lastname': request.form.get("lastname"), 'username': request.form.get("username").lower(),
                   'password': generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)})

        row = db.execute("SELECT * FROM users WHERE username = :username", {'username': request.form.get("username")}).fetchall()

        session["user_id"] = row[0]["user_id"]

        db.commit()

        return redirect("/")

    else:

        return render_template("register.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():

    if request.method == "GET":

        return redirect("/")

    else:
        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

        if not request.form.get("search"):
            return redirect("/")

        rows = db.execute("SELECT DISTINCT isbn, title, author FROM books WHERE LOWER(isbn) LIKE :search OR LOWER(title) LIKE :search OR LOWER(author) LIKE :search", {'search': '%' + request.form.get("search").lower() + '%'}).fetchall()

        if rows != 0:
            return render_template("search.html", rows=rows, search=request.form.get("search"), user=user)
        else:
            return render_template("search.html", search=request.form.get("search"), user=user)


@app.route("/book/<title>", methods=["GET", "POST"])
@login_required
def book(title):

    if request.method == "GET":
        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

        rows = db.execute("SELECT * FROM books WHERE title = :title", {'title': title}).fetchall()

        rate = db.execute("SELECT firstname, review, rating FROM review JOIN users ON review.user_id = users.user_id WHERE book_id = :id", {'id': rows[0]["id"]}).fetchall()

        return render_template("book.html", rows = rows, user=user, rate=rate)

    else:

        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

        rows = db.execute("SELECT * FROM books WHERE title = :title", {'title': title}).fetchall()

        if not request.form.get("rating"):
            return render_template("error.html", message = "Must provide rating", user=user)

        if not request.form.get("comment"):


            db.execute("INSERT INTO review (user_id, book_id, rating) VALUES(:user_id, :book_id, :rating)", {'user_id': int(session["user_id"]), 'book_id': rows[0]["id"], 'rating': int(request.form.get("rating"))})
        else:

            db.execute("INSERT INTO review (user_id, book_id, review, rating) VALUES(:user_id, :book_id, :review, :rating)", {'user_id': int(session["user_id"]), 'book_id': rows[0]["id"], 'review': request.form.get("comment"), 'rating': int(request.form.get("rating"))})

        db.commit()

        return redirect(url_for('book', title=rows[0]["title"]))
