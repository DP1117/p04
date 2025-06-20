from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
import os
import pandas as pd
import numpy as np
import warnings
import json

warnings.filterwarnings('ignore')
pd.set_option('display.max_columns',None)
#init_notebook_mode(connected=True)

df=pd.read_csv('songs_normalize.csv')

app = Flask(__name__)
app.secret_key = 'supersecretkey'

DB_PATH = 'users.db'
def init_db():
    if not os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            ''')
            conn.commit()



@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
                conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return redirect(url_for('error', type='nameTaken'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
            user = c.fetchone()
            if user:
                session['user'] = username
                return redirect(url_for('home'))
            else:
                return redirect(url_for('error', type='wrongCredentials'))
    return render_template('login.html')
    
@app.route('/error')
def error():
    errorType = request.args.get('type')

    return render_template('error.html',
        notLoggedIn=(errorType == 'notLoggedIn'),
        wrongCredentials=(errorType == 'wrongCredentials'),
        nameTaken=(errorType == 'nameTaken'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/visualize')
def visualize():
    if 'user' not in session:
        return redirect(url_for('error', type='notLoggedIn'))
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    data = df[numeric_cols].dropna().to_dict(orient='records')
    return render_template('visualize.html', data=data, columns=numeric_cols)

@app.route('/histo')
def histo():
    if 'user' not in session:
        return redirect(url_for('error', type='notLoggedIn'))
    if 'popularity' not in df.columns:
        return "Popularity column not found in the dataset."
    data = df[['popularity']].dropna().to_dict(orient='records')
    return render_template('histo.html', data=data)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/matrix')
def matrix():
    if 'user' not in session:
        return redirect(url_for('error', type='notLoggedIn'))
    features = ['popularity', 'danceability', 'energy', 'loudness', 'speechiness',
                'acousticness', 'liveness', 'valence', 'tempo']
    data = df[features].dropna().to_dict(orient='records')
    return render_template('matrix.html', data=data, features=features)

@app.route('/correlationmatrix')
def correlationmatrix():
    if 'user' not in session:
        return redirect(url_for('error', type='notLoggedIn'))
    corr_matrix = df.corr(numeric_only=True).round(3)
    labels = corr_matrix.columns.tolist()
    matrix_data = []

    for i, row in enumerate(labels):
        for j, col in enumerate(labels):
            matrix_data.append({
                "row": row,
                "col": col,
                "value": corr_matrix.iloc[i, j]
            })

    return render_template("correlationmatrix.html", labels=labels, matrix=matrix_data)

@app.route('/topcharts')
def topcharts():
    subset = df[['artist', 'genre', 'song', 'popularity']].dropna()

    top_songs = (subset.sort_values(by='popularity', ascending=False)
                 .head(15)[['song', 'artist', 'popularity']])

    top_artists = (subset.groupby('artist')['popularity']
                   .sum()
                   .sort_values(ascending=False)
                   .head(15)
                   .reset_index())

    top_genres = (subset['genre'].value_counts()
                  .head(15)
                  .reset_index()
                  .rename(columns={'index': 'genre', 'genre': 'count'}))

    return render_template(
        "topcharts.html",
        songs=top_songs.to_dict(orient="records"),
        artists=top_artists.to_dict(orient="records"),
        genres=top_genres.to_dict(orient="records")
    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
