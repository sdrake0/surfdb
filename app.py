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
    # Fetch the top 10 most popular maps and highest rated maps from the database
    popular_maps =  db.execute("""
        SELECT maps.map_id, maps.name, maps.tier, maps.type, maps.mapper, maps.youtube, maps.stages, maps.bonuses, COUNT(ratings.map_id) AS rating_count
        FROM maps
        JOIN ratings ON maps.map_id = ratings.map_id
        GROUP BY maps.map_id, maps.name, maps.tier, maps.type, maps.mapper, maps.youtube, maps.stages, maps.bonuses
        ORDER BY rating_count DESC
        LIMIT 10
    """)
    
    best_maps = db.execute("""
        SELECT maps.map_id, maps.name, maps.tier, maps.type, maps.mapper, maps.youtube, maps.stages, maps.bonuses, AVG(ratings.rating) AS average_rating
        FROM maps
        JOIN ratings ON maps.map_id = ratings.map_id
        GROUP BY maps.map_id, maps.name, maps.tier, maps.type, maps.mapper, maps.youtube, maps.stages, maps.bonuses
        ORDER BY average_rating DESC
        LIMIT 10
    """)

    return render_template('index.html', popular_maps=popular_maps, best_maps=best_maps)

@app.route('/map/<string:map_name>', methods=['GET', 'POST'])
def map_page(map_name):
    # Fetch the map data from the database - Used ChatGPT to generate part of this SQL query
    map_data = db.execute("""SELECT maps.*, 
                                COUNT(ratings.map_id) AS rating_count, 
                                AVG(ratings.rating) AS average_rating,
                                AVG(ratings.tier) AS usertier,
                                (SELECT surftype 
                                    FROM ratings r 
                                    WHERE r.map_id = maps.map_id 
                                    GROUP BY surftype 
                                    ORDER BY COUNT(surftype) DESC 
                                    LIMIT 1) AS surftype
                            FROM maps 
                            LEFT JOIN ratings ON maps.map_id = ratings.map_id 
                            WHERE maps.name = ?
                            GROUP BY maps.map_id
                            """, map_name)
    
    # Check if the map exists
    if not map_data:
        return render_template('nomap.html')
    
    # Get the only result
    map_data = map_data[0]

    loggedin = False

    types = ['Unit', 'Tech', 'Maxvel', 'Combo', 'Other']
    # Note user logged in if in session
    if 'userid' in session:
        user_ratings = db.execute("SELECT * FROM ratings WHERE map_id =? AND userid =?", map_data['map_id'], session['userid'])
        user_data = user_ratings[0] if user_ratings else None
        loggedin = True
    else:
        user_data = None
    
    if request.method == 'POST':
        # Get the user's rating, tier, and type from the form or request data
        if request.form.get('rating'):
            userrating = float(request.form.get('rating'))
        else:
            userrating = 0
        
        if request.form.get('tier'):
            usertier = float(request.form.get('tier'))
        else:
            usertier = 0

        usertype = request.form.get('type')

        # Check if the user has already rated the map, then update or insert a new rating
        if loggedin:
            previous_rating = db.execute("SELECT userid FROM ratings WHERE map_id = ? AND userid = ?", map_data['map_id'], session['userid'])

            if not previous_rating:
                db.execute("INSERT INTO ratings (map_id, userid) VALUES (?, ?)", map_data['map_id'], session['userid'])
            
            if 1 <= userrating <= 10:
                db.execute("UPDATE ratings SET rating = ? WHERE map_id = ? AND userid = ?", userrating, map_data['map_id'], session['userid'])
            if 1 <= usertier < 9:
                db.execute("UPDATE ratings SET tier = ? WHERE map_id = ? AND userid = ?", usertier, map_data['map_id'], session['userid'])
            if usertype in types:
                db.execute("UPDATE ratings SET surftype =? WHERE map_id =? AND userid =?", usertype, map_data['map_id'], session['userid'])
        
        return redirect(url_for('map_page', map_name=map_data['name']))

    return render_template('map.html', map_data=map_data, user_data=user_data, loggedin=loggedin)

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

@app.route('/search', methods=['GET'])
def search():
    if request.method == 'GET':
        # Fetch search parameters from the request
        map_name = request.args.get('map')
        map_type = request.args.get('type')
        map_tier = request.args.get('tier')
        sort = request.args.get('sort')

        # Build the SQL query - used ChatGPT to generate this SQL query
        query = """
            SELECT m.*, 
                    AVG(r.rating) AS average_rating, 
                    AVG(r.tier) AS usertier,
                    CASE 
                        WHEN LOWER(m.name) = LOWER(:name) THEN 0
                        WHEN LOWER(m.name) LIKE LOWER(:name) || '%' THEN 1
                        WHEN LOWER(m.name) LIKE '%' || LOWER(:name) || '%' THEN 2
                        ELSE 3 
                    END AS priority,
                    INSTR(LOWER(m.name), LOWER(:name)) AS name_position
            FROM maps m
            LEFT JOIN ratings r ON m.map_id = r.map_id
            WHERE 1=1
        """
        params = {"name": map_name if map_name else ""}

        # Conditionally add parameters to the query and dictionary
        if map_name:
            query += " AND LOWER(m.name) LIKE LOWER(:name_like)"
            params["name_like"] = f"%{map_name}%"
        
        if map_type:
            query += " AND m.type = :type"
            params["type"] = map_type
        
        if map_tier:
            query += " AND m.tier = :tier"
            params["tier"] = map_tier

        query += " GROUP BY m.map_id"

        # Add sorting based on priority and other criteria
        if sort:
            if sort == "hightier":
                query += " ORDER BY priority, name_position, m.tier DESC"
            elif sort == "lowtier":
                query += " ORDER BY priority, name_position, m.tier ASC"
            elif sort == "highrate":
                query += " ORDER BY priority, name_position, average_rating DESC"
            elif sort == "lowrate":
                query += " ORDER BY priority, name_position, average_rating ASC"
            else:
                query += " ORDER BY priority, name_position, m.name"
        else:
            # Default sorting if no sort parameter is provided
            query += " ORDER BY priority, name_position, m.name"

        query += " LIMIT 50"

        # Execute the query with only the parameters that are actually provided
        results = db.execute(query, **params)
        
        return render_template('search_results.html', query=map_name, search_type=map_type, tier=map_tier, results=results)
    else:
        return render_template('search_results.html', query=map_name, search_type=map_type, tier=map_tier, results=results)


@app.route("/howto")
def howto():
    return render_template('howto.html')

@app.route("/request", methods=['GET', 'POST'])
def requestform():
    return render_template('requestform.html')

@app.route("/profile")
def profile():
    if 'userid' not in session:
        return redirect('/')
    
    if session['userid'] not in db.execute("SELECT user_id FROM profile"):
        db.execute("INSERT INTO profile (user_id) VALUES (?)", session['userid'])
    
    user_profile = db.execute("SELECT * FROM profile WHERE user_id = ?", session['userid'])[0]

    favoritemaps = db.execute("SELECT name, rating FROM ratings JOIN maps ON maps.map_id = ratings.map_id WHERE userid = ? ORDER BY rating DESC LIMIT 10", session['userid'])

    if db.execute("SELECT rating FROM ratings WHERE userid = ?", session['userid']):
        totalratings = int(db.execute("SELECT COUNT(rating) FROM ratings WHERE userid = ?", (session['userid'],))[0]['COUNT(rating)'])

    return render_template('profile.html', user_profile=user_profile, favoritemaps=favoritemaps, totalratings=totalratings)

@app.route("/editprofile", methods=['GET', 'POST'])
def editprofile():
    if 'userid' not in session:
        return redirect('/')
    
    if request.method == 'POST':
        if request.form.get('username'):
            username = request.form.get('username')
            db.execute("UPDATE profile SET username = ? WHERE user_id = ?", username, session['userid'])

        if request.form.get('age').isdigit():
            age = int(request.form.get('age'))
            db.execute("UPDATE profile SET age = ? WHERE user_id = ?", age, session['userid'])

        if request.form.get('gender').isdigit():
            if 0 <= int(request.form.get('gender')) <= 100:
                gender = int(request.form.get('gender'))
                db.execute("UPDATE profile SET gender = ? WHERE user_id = ?", gender, session['userid'])
        
        return redirect('/profile')
    
    user_profile = db.execute("SELECT * FROM profile WHERE user_id = ?", session['userid'])[0]

    return render_template('editprofile.html', user_profile=user_profile)

if __name__ == '__main__':
    app.run(debug=True)