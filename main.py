from flask import Flask, request, render_template, redirect, url_for, flash, abort, session
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from functools import wraps
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import os

import flask_sqlalchemy
print(flask_sqlalchemy.__version__)


Base = declarative_base()

from flask_wtf import FlaskForm
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "*(DHASIODHN*DSYA*()D")
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##SET UP FLASK-LOGIN
login_manager = LoginManager()
login_manager.init_app(app)

## Set up Flask Gravatar

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='monsterid',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


# CREATE USER TABLE/DECLARE A MODEL
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(150), nullable=False)
    posts = db.relationship("BlogPost", back_populates='author') ######## 1 #########
    comments = db.relationship("Comment", back_populates='comment_author') ######## 3 #########

# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = (db.Column(db.Integer, db.ForeignKey('users.id'))) #************* KEY A *************

    author = db.relationship("User", back_populates='posts') ######## 1 #########
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = db.relationship("Comment", back_populates='parent_post') ######## 2 #########

# CREATE COMMENT TABLE
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = (db.Column(db.Integer, db.ForeignKey('blog_posts.id'))) #************* KEY B *************
    author_id = (db.Column(db.Integer, db.ForeignKey('users.id'))) #************* KEY C *************
    text = db.Column(db.Text, unique=False, nullable=False)

    parent_post = db.relationship("BlogPost", back_populates='comments') ######## 2 #########
    comment_author = db.relationship("User", back_populates='comments')  ######## 3 #########

db.create_all()

# user = User.query.get(1)
# blog_posts = user.blog_post
# for blog_post in blog_posts:
#     print(blog_post)
#     print('hi')

def admin_only(f):
    @wraps(f)
    def wrapper_function(*args, **kwargs):
        if current_user.id == 1:
            return f(*args, **kwargs)
        return abort(403)
    return wrapper_function


# 1. A user loader tells Flask-Login how to get a specific user object from the ID that is stored in the session cookie

# 2. When you log in, Flask-Login creates a cookie that contains your User.id. This is just an id, a string, not the
# User object itself; at this point, it doesn't know your name or email etc. // When you go to a new page that tries
# to access the current_user and its properties, as when we print the user's name on the secrets page, Flask-Login
# needs to create a User object from the stored user_id to do so. It does by calling the user_loader decorated function.
# So, even though we don't explicitly call that function, in fact we've used it on every page.

  # in flask 2.0x user id is automatically saved in session under _user_id
    # user_id is just the primary key of our user table

@login_manager.user_loader
def load_user(user_id):             # get user id from session(cookie) using user_id
    return User.query.get(user_id)  # retrieve user object from database

@app.route('/', methods=['POST', 'GET'])
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    new_user = User(
        username=form.username.data,
        email=form.email.data,
        password=form.password.data
    )
    if form.validate_on_submit():
        if User.query.filter_by(email=new_user.email).first():
            print('exist')
            flash("You've already signed up with that email. Log in instead!")
            return redirect(url_for('login'))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        entered_email = form.email.data
        entered_password = form.password.data
        user = User.query.filter_by(email=entered_email).first()
        print(entered_email)
        if entered_password == user.password:
            login_user(user)
            return redirect(url_for('get_all_posts'))
        else:
            flash('Incorrect login details. Please try again.')
            return render_template('login.html', form=form)
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['POST', 'GET'])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)

    if form.validate_on_submit():
        if current_user.is_authenticated:
            comment = Comment(
                text=form.body.data,
                parent_post=requested_post,
                comment_author=current_user,
            )
            db.session.add(comment)
            db.session.commit()
            return render_template("post.html", form=form, post=requested_post)
        else:
            flash('You need to log in or create an account to comment')
            form = LoginForm()
            return redirect(url_for("login", form=form))
    return render_template("post.html", form=form, post=requested_post)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/new-post", methods=['POST', 'GET'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():

        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user, #the author property of BlogPost is now a User object.
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))

    return render_template("make-post.html", form=form)

@admin_only
@app.route("/edit-post/<int:post_id>")
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)

@admin_only
@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route('/secrets')
def download_file():
    return render_template('secrets.html')



if __name__ == "__main__":
    app.run()
