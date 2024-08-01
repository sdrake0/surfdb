from flask import Flask, render_template, url_for, request, jsonify, session, redirect, abort
from flask_session import Session
from google.oauth2 import id_token
from google.auth.transport import requests
from cs50 import SQL

#configure application
app = Flask(__name__, static_folder='static')
CLIENT_ID = '370465136464-d21p30j6pjg46adpmfqc50qjs7h30mvi.apps.googleusercontent.com'


# Configure session to use filesystem for storing session data
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///surf.db")

@app.route('/')
def home():
    # Fetch the top 10 most popular maps from the database
    popular_maps =  db.execute("""
        SELECT maps.map_id, maps.name, maps.tier, maps.type, maps.mapper, maps.youtube, maps.steam, maps.bonuses, COUNT(ratings.map_id) AS rating_count
        FROM maps
        JOIN ratings ON maps.map_id = ratings.map_id
        GROUP BY maps.map_id, maps.name, maps.tier, maps.type, maps.mapper, maps.youtube, maps.steam, maps.bonuses
        ORDER BY rating_count DESC
        LIMIT 10
    """)
    
    best_maps = db.execute("""
        SELECT maps.map_id, maps.name, maps.tier, maps.type, maps.mapper, maps.youtube, maps.steam, maps.bonuses, AVG(ratings.rating) AS average_rating
        FROM maps
        JOIN ratings ON maps.map_id = ratings.map_id
        GROUP BY maps.map_id, maps.name, maps.tier, maps.type, maps.mapper, maps.youtube, maps.steam, maps.bonuses
        ORDER BY average_rating DESC
        LIMIT 10
    """)

    return render_template('index.html', popular_maps=popular_maps, best_maps=best_maps)

@app.route('/map/<string:map_name>')
def map_page(map_name):
    # Fetch the map data from the database
    map_data = db.execute("SELECT * FROM maps WHERE name = ?", map_name)
    
    # Check if the map exists
    if not map_data:
        abort(404)
    
    # Get the first (and presumably only) result
    map_data = map_data[0]
    
    return render_template('map.html', map=map_data)

@app.route('/go-to-map', methods=['POST'])
def go_to_map():
    # Get the map name from the form or request data
    map_name = request.form.get('map_name')
    
    # Redirect to the map page
    return redirect(url_for('map_page', map_name=map_name))

@app.route('/tokensignin', methods=['POST'])
def tokensignin():
    session.clear()
    token = request.json.get('id_token')
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        googleid = idinfo['sub']
        email = idinfo['email']
        name = idinfo['name']

        rows = db.execute("SELECT * FROM users WHERE email = ?", email)

        if not rows:
            db.execute("INSERT INTO users (googleid, email, name) VALUES (?, ?, ?)", googleid, email, name)
            rows = db.execute("SELECT * FROM users WHERE email = ?", email)
        
        session['userid'] = rows[0]['id']

        return jsonify({'message': 'User authenticated'})
    except ValueError:
        # Invalid token
        return jsonify({'message': 'Invalid token'}), 400

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to home page
    return redirect("/")

if __name__ == '__main__':
    app.run(debug=True)