import os
import logging
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import markdown
from datetime import datetime
import pymysql

pymysql.install_as_MySQLdb()

# Set up logging
logging.basicConfig(filename='/home/chanariesj/myblog/error.log', level=logging.DEBUG)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://chanariesj:phiLAWsophy2019$@chanariesj.mysql.pythonanywhere-services.com/chanariesj$default'
app.config['SQLALCHEMY_POOL_RECYCLE'] = 299
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE_DIR, "posts")

class Post:
    def __init__(self, filename):
        self.filename = filename
        self.metadata = {}
        self.raw_content = ""
        self.content = ""
        self._parse()

    def _parse(self):
        try:
            with open(os.path.join(POSTS_DIR, self.filename), "r") as f:
                content = f.read()

            # Split content into metadata and body
            parts = content.split('---\n', 2)
            if len(parts) < 3:
                raise ValueError(f"Invalid format in {self.filename}")

            metadata_raw, self.raw_content = parts[1], parts[2]

            # Parse metadata
            for line in metadata_raw.strip().splitlines():
                key, value = line.split(':', 1)
                self.metadata[key.strip()] = value.strip()

            logging.debug(f"Parsed file: {self.filename}")
            logging.debug(f"Metadata: {self.metadata}")
            logging.debug(f"Raw content: {self.raw_content[:100]}")
        except Exception as e:
            logging.error(f"Error parsing file {self.filename}: {str(e)}")
            raise

def get_posts():
    posts = []
    try:
        for filename in os.listdir(POSTS_DIR):
            if filename.endswith(".md"):
                logging.debug(f"Found post file: {filename}")
                try:
                    posts.append(Post(filename))
                except Exception as e:
                    logging.error(f"Error processing {filename}: {str(e)}")
        logging.debug(f"Total posts found: {len(posts)}")
        return sorted(posts, key=lambda x: datetime.strptime(x.metadata.get("date", "1970-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S"), reverse=True)
    except Exception as e:
        logging.error(f"Error in get_posts: {str(e)}")
        raise

# Custom Markdown filter
def markdown_filter(text):
    return markdown.markdown(text)

app.jinja_env.filters['markdown'] = markdown_filter

@app.route("/")
def index():
    try:
        posts = get_posts()
        for post in posts:
            logging.debug(f"Post title: {post.metadata.get('title')}")
            logging.debug(f"Post content (first 100 chars): {post.content[:100]}")
        return render_template("index.html", posts=posts)
    except Exception as e:
        logging.error(f"Error in index route: {str(e)}")
        return f"An error occurred: {str(e)}", 500

@app.route("/post/<filename>")
def post(filename):
    try:
        posts = get_posts()
        current_post = next((post for post in posts if post.filename == filename), None)
        if current_post is None:
            return "Post not found", 404
        logging.debug(f"Rendering post: {filename}")
        logging.debug(f"Post title: {current_post.metadata.get('title')}")
        logging.debug(f"Post content (first 100 chars): {current_post.content[:100]}")
        return render_template("post.html", post=current_post)
    except Exception as e:
        logging.error(f"Error in post route: {str(e)}")
        return f"An error occurred: {str(e)}", 500

@app.route('/search')
def search():
    query = request.args.get('query')
    if query:
        posts = get_posts()
        results = [post for post in posts if query.lower() in post.content.lower() or query.lower() in post.metadata.get('title', '').lower()]
        return render_template('search_results.html', query=query, results=results)
    return redirect(url_for('index'))

@app.route('/category/<category>')
def category(category):
    posts = [post for post in get_posts() if post.metadata.get('category', '').lower() == category.lower()]
    return render_template('category.html', category=category, posts=posts)

@app.route('/tag/<tag>')
def tag(tag):
    posts = [post for post in get_posts() if tag.lower() in [t.strip().lower() for t in post.metadata.get('tags', '').split(',')]]
    return render_template('tag.html', tag=tag, posts=posts)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == "__main__":
    app.run(debug=True)