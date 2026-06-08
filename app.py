import pickle
import re
import requests
from flask import Flask, render_template, request, redirect, session
import sqlite3

# load model
model = pickle.load(open("model/model.pkl", "rb"))
vectorizer = pickle.load(open("model/vectorizer.pkl", "rb"))

app = Flask(__name__)
app.secret_key = "secret123"
API_KEY = "d02a4237a3af489f86ee029842840c5e"
def init_db():

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    # USERS TABLE

    cursor.execute('''

    CREATE TABLE IF NOT EXISTS users(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT
    )

    ''')

    # HISTORY TABLE

    cursor.execute('''

    CREATE TABLE IF NOT EXISTS history(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER,

        article TEXT,

        prediction TEXT

    )

    ''')

    conn.commit()

    conn.close()

def clean_text(text):
    text = text.lower()
    text = re.sub(r'http\\S+', '', text)
    text = re.sub(r'[^a-zA-Z]', ' ', text)
    text = re.sub(r'\\s+', ' ', text)
    return text

@app.route("/")
def home():
    return render_template("project.html")

@app.route("/predict", methods=["POST"])
def predict():

    news = request.form["news"]

    if not news.strip():

        return render_template(
            "project.html",
            prediction="Please enter news text"
        )

    news_clean = clean_text(news)

    # Convert cleaned text into TF-IDF vector

    news_vector = vectorizer.transform([news_clean])

    prediction = model.predict(news_vector)

    if prediction[0] == 0:

        result = "Fake News"

    else:

        result = "Real News"


    # SAVE HISTORY

    if "user_id" in session:

        conn = sqlite3.connect("database.db")

        cursor = conn.cursor()

        cursor.execute(

            "INSERT INTO history(user_id,article,prediction) VALUES(?,?,?)",

            (session["user_id"], news, result)

        )

        conn.commit()

        conn.close()


    return render_template(

        "project.html",

        prediction=result

    )

@app.route("/latest-news")

def latest_news():

    url = "https://newsapi.org/v2/top-headlines?country=us&apiKey=YOUR_API_KEY"

    response = requests.get(url)

    data = response.json()


    # CHECK IF ARTICLES EXIST

    if not data.get("articles"):

        return render_template(

            "live_news.html",

            article="No live news available right now.",

            prediction="No Prediction"

        )


    article = data["articles"][0]


    news = article.get("content")


    if not news:

        news = article.get("title")


    if not news:

        news = "No content available."


    news_clean = clean_text(news)

    news_vector = vectorizer.transform([news_clean])

    prediction = model.predict(news_vector)


    if prediction[0] == 0:

        result = "Fake News"

    else:

        result = "Real News"


    return render_template(

        "live_news.html",

        article=news,

        prediction=result

    )

@app.route("/live-news")
def live_news():

    url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize=1&apiKey={API_KEY}"

    response = requests.get(url)

    data = response.json()

    if len(data["articles"]) == 0:

        return render_template(

            "live_news.html",

            article="No live news available right now.",

            prediction="No Prediction"

    )

    article = data["articles"][0]

    news_text = (
        str(article["title"]) + " " +
        str(article["description"]) + " " +
        str(article["content"])
    )

    news_clean = clean_text(news_text)

    news_vector = vectorizer.transform([news_clean])

    prediction = model.predict(news_vector)

    if prediction[0] == 0:
        result = "Fake News"
    else:
        result = "Real News"

    return render_template(
        "live_news.html",
        article=news_text,
        prediction=result
    )

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/signup", methods=["GET", "POST"])

def signup():

    error = ""

    success = ""

    if request.method == "POST":

        username = request.form["username"]

        email = request.form["email"]

        password = request.form["password"]

        conn = sqlite3.connect("database.db")

        cursor = conn.cursor()

        # EMAIL CHECK

        cursor.execute(

            "SELECT * FROM users WHERE email=?",

            (email,)

        )

        existing_email = cursor.fetchone()

        # USERNAME CHECK

        cursor.execute(

            "SELECT * FROM users WHERE username=?",

            (username,)

        )

        existing_username = cursor.fetchone()

        if existing_email:

            error = "Email already registered"

        elif existing_username:

            error = "Username already taken"

        else:

            cursor.execute(

                "INSERT INTO users(username,email,password) VALUES(?,?,?)",

                (username,email,password)

            )

            conn.commit()

            success = "Signup Successful! Please Login."

        conn.close()

    return render_template(

        "signup.html",

        error=error,

        success=success

    )

@app.route("/login", methods=["GET", "POST"])

def login():

    error = ""

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]

        conn = sqlite3.connect("database.db")

        cursor = conn.cursor()

        cursor.execute(

            "SELECT * FROM users WHERE email=? AND password=?",

            (email,password)

        )

        user = cursor.fetchone()

        conn.close()

        if user:

            session["user_id"] = user[0]

            session["username"] = user[1]

            return redirect("/")

        else:

            error = "Invalid Email or Password"

    return render_template(

        "login.html",

        error=error

    )


@app.route("/logout")

def logout():

    session.clear()

    return redirect("/")

@app.route("/profile")

def profile():

    if "user_id" not in session:

        return redirect("/login")

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    cursor.execute(

        "SELECT username,email FROM users WHERE id=?",

        (session["user_id"],)

    )

    user = cursor.fetchone()


    cursor.execute(

        "SELECT article,prediction FROM history WHERE user_id=? ORDER BY id DESC",

        (session["user_id"],)

    )

    history = cursor.fetchall()

    conn.close()

    return render_template(

        "profile.html",

        user=user,

        history=history

    )


@app.route("/history")

def history():

    if "user_id" not in session:

        return redirect("/login")

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    cursor.execute(

        "SELECT article,prediction FROM history WHERE user_id=?",

        (session["user_id"],)

    )

    data = cursor.fetchall()

    conn.close()

    return render_template(

        "history.html",

        history=data

    )



init_db()

if __name__ == "__main__":
    app.run(debug=True)