"""Example flask app that stores passwords hashed with Bcrypt. Yay!"""

import os

from flask import Flask, render_template, redirect, session, flash
from flask_debugtoolbar import DebugToolbarExtension

from models import connect_db, db, User, Note
from forms import RegisterForm, LoginForm, CSRFProtectForm, NoteForm

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgresql:///flask_notes")
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = "abc123"

connect_db(app)
db.create_all()

toolbar = DebugToolbarExtension(app)


@app.get('/')
def homepage():
    """Redirect to register page"""

    return redirect('/register')


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user: produce form & handle form submission."""

    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data

        user = User.register(username, password, email, first_name, last_name)
        db.session.add(user)
        db.session.commit()

        session["username"] = user.username

        return redirect(f"/users/{username}")

    else:
        return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Produce login form or handle login."""

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # authenticate will return a user or False
        user = User.authenticate(username, password)

        if user:
            session["username"] = user.username  # keep logged in
            return redirect(f"/users/{user.username}")

        else:
            form.username.errors = ["Bad name/password"]

    return render_template("login.html", form=form)

# ===================================== USER ROUTE ==========================


@app.get('/users/<username>')
def user_info(username):
    """ Hidden page for logged-in users only """

    user = User.query.get_or_404(username)
    form = CSRFProtectForm()
    notes = user.notes

    if "username" not in session or session["username"] != user.username:
        flash("You must be logged in to view!")
        return redirect("/")
    else:
        return render_template(
            "user.html",
            user=user,
            form=form,
            notes=notes)


@app.post("/logout")
def logout():
    """Logs user out and redirects to homepage."""

    form = CSRFProtectForm()

    if form.validate_on_submit():
        # Remove "user_id" if present, but no errors if it wasn't
        session.pop("username", None)

    return redirect("/")


@app.post('/users/<username>/delete')
def delete_user(username):
    """delete user from database and delete all notes. 
    Clear user session info and redirect to ('/')"""

    user = User.query.get_or_404(username)
    if "username" not in session or session["username"] != user.username:
        flash("You cannot perform this action!")
        return redirect("/")

    form = CSRFProtectForm()
    if form.validate_on_submit():

        db.session.delete(user)
        db.session.delete(user.notes)
        db.session.commit()

        return redirect('/')


# ===================================== NOTES ROUTE ==========================

@app.route('/users/<username>/notes/add', methods=["GET", "POST"])
def create_user_note(username):
    """ Display and handle form for notes """

    user = User.query.get_or_404(username)
    if "username" not in session or session["username"] != user.username:
        flash("You cannot perform this action!")
        return redirect("/")

    form = NoteForm()

    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        owner = user.username

        note = Note(
            title=title,
            content=content,
            owner=owner
        )

        db.session.add(note)
        db.session.commit()

        flash("Added new note!")
        return redirect(f'/users/{username}')
    else:
        return render_template(
            '/notes/add_note.html',
            user=user,
            form=form
        )


@app.route('/notes/<int:note_id>/update', methods=["GET", "POST"])
def edit_note(note_id):
    """ Display and handle form for editing note """

    note = Note.query.get_or_404(note_id)
    if "username" not in session or session["username"] != note.owner:
        flash("You cannot perform this action!")
        return redirect("/")

    form = NoteForm()

    if form.validate_on_submit():
        note.title = form.title.data
        note.content = form.content.data
        note.owner = note.owner

        db.session.commit()

        flash("Edited note!")
        return redirect(f'/users/{note.owner}')
    else:
        return render_template(
            '/notes/edit_note.html',
            note=note,
            form=form
        )


@app.post('/notes/<int:note_id>/delete')
def delete_note(note_id):
    """ Delete note and redirect """

    note = Note.query.get_or_404(note_id)
    if "username" not in session or session["username"] != note.owner:
        flash("You cannot perform this action!")
        return redirect("/")

    form = CSRFProtectForm()

    if form.validate_on_submit():

        db.session.delete(note)
        db.session.commit()

        return redirect(f'/users/{note.owner}')

    else:
        flash("You are unauthorized!")
        return redirect("/")
