import os
from flask import Flask, render_template, url_for, request, jsonify, session, redirect, abort
from flask_session import Session
from google.oauth2 import id_token
from google.auth.transport import requests
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func
from db import db  # Import `db` from `db.py`
from models import Map, Rating, User, Profile

# Configure application
app = Flask(__name__, static_folder='static')
CLIENT_ID = '370465136464-d21p30j6pjg46adpmfqc50qjs7h30mvi.apps.googleusercontent.com'

# Configure session to use filesystem for storing session data
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure SQLAlchemy to use PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://u7cu09fjkpg1qb:p780e9b4cd28b981a8bb95b57d8670c6007d977ec1f5e239e318ea8335bc76e70@c9uss87s9bdb8n.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d6egq4keh844gb' # os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database and migration objects
db.init_app(app)  # Initialize `db` with the app
migrate = Migrate(app, db)

def is_mobile():
    user_agent = request.headers.get('User-Agent')
    mobile_browsers = ['iphone', 'android', 'blackberry', 'nokia', 'opera mini', 'windows phone', 'silk']

    if any(browser in user_agent.lower() for browser in mobile_browsers):
        return True
    return False

@app.route('/')
def home():
    # Fetch the top 10 most popular maps based on rating count
    popular_maps = db.session.query(
        Map.map_id, Map.name, Map.tier, Map.type, Map.mapper, Map.youtube, Map.stages, Map.bonuses,
        db.func.count(Rating.map_id).label('rating_count')
    ).join(Rating).group_by(
        Map.map_id, Map.name, Map.tier, Map.type, Map.mapper, Map.youtube, Map.stages, Map.bonuses
    ).order_by(
        db.func.count(Rating.map_id).desc()
    ).limit(10).all()
    
    # Fetch the top 10 best-rated maps based on average rating
    best_maps = db.session.query(
        Map.map_id, Map.name, Map.tier, Map.type, Map.mapper, Map.youtube, Map.stages, Map.bonuses,
        db.func.avg(Rating.rating).label('average_rating')
    ).join(Rating).group_by(
        Map.map_id, Map.name, Map.tier, Map.type, Map.mapper, Map.youtube, Map.stages, Map.bonuses
    ).order_by(
        db.func.avg(Rating.rating).desc()
    ).limit(10).all()

    if is_mobile():
        return render_template('mobileindex.html', popular_maps=popular_maps, best_maps=best_maps)
    else:
        return render_template('index.html', popular_maps=popular_maps, best_maps=best_maps)

@app.route('/map/<string:map_name>', methods=['GET', 'POST'])
def map_page(map_name):
    # Construct the subquery for the most common surf type
    surf_type_subquery = db.session.query(
        Rating.surftype,
        func.count().label('count')
    ).filter(Rating.map_id == Map.map_id)\
     .group_by(Rating.surftype)\
     .order_by(func.count().desc())\
     .limit(1).subquery()

    # Fetch the map data from the database
    map_data_query = db.session.query(
        Map,
        func.count(Rating.map_id).label('rating_count'),
        func.avg(Rating.rating).label('average_rating'),
        func.avg(Rating.tier).label('usertier')
    ).outerjoin(Rating, Map.map_id == Rating.map_id)\
     .filter(Map.name == map_name)\
     .group_by(Map.map_id)

    # Execute the query
    map_data = map_data_query.first()

    # Fetch the most common surf type separately
    surf_type_query = db.session.query(
        func.coalesce(surf_type_subquery.c.surftype, 'Unknown')
    ).scalar()

    # Check if the map exists
    if not map_data:
        return render_template('nomap.html')

    # Convert the map_data tuple to a dictionary-like object
    map_data_dict = {
        'map_id': map_data[0].map_id,
        'name': map_data[0].name,
        'tier': map_data[0].tier,
        'type': map_data[0].type,
        'mapper': map_data[0].mapper,
        'youtube': map_data[0].youtube,
        'stages': map_data[0].stages,
        'bonuses': map_data[0].bonuses,
        'rating_count': map_data.rating_count,
        'average_rating': map_data.average_rating,
        'usertier': map_data.usertier,
        'surftype': surf_type_query
    }

    loggedin = False
    types = ['Unit', 'Tech', 'Maxvel', 'Combo', 'Other']

    # Note user logged in if in session
    if 'userid' in session:
        user_ratings = Rating.query.filter_by(map_id=map_data_dict['map_id'], userid=session['userid']).first()
        user_data = user_ratings if user_ratings else None
        loggedin = True
    else:
        user_data = None

    if request.method == 'POST':
        # Get the user's rating, tier, and type from the form or request data
        userrating = request.form.get('rating', 0)
        usertier = request.form.get('tier', 0)
        usertype = request.form.get('type')

        try:
            userrating = float(userrating)
            usertier = float(usertier)

            if loggedin:
                previous_rating = Rating.query.filter_by(map_id=map_data_dict['map_id'], userid=session['userid']).first()

                if not previous_rating:
                    new_rating = Rating(
                        map_id=map_data_dict['map_id'],
                        userid=session['userid'],
                        rating=userrating if 1 <= userrating <= 10 else None,
                        tier=usertier if 1 <= usertier < 9 else None,
                        surftype=usertype if usertype in types else None
                    )
                    db.session.add(new_rating)
                else:
                    # Update the existing rating
                    if 1 <= userrating <= 10:
                        previous_rating.rating = userrating
                    if 1 <= usertier < 9:
                        previous_rating.tier = usertier
                    if usertype in types:
                        previous_rating.surftype = usertype

                db.session.commit()

        except ValueError:
            # Handle the case where rating or tier are not valid numbers
            pass

        return redirect(url_for('map_page', map_name=map_data_dict['name']))
    if is_mobile():
        return render_template('mobilemap.html', map_data=map_data_dict)
    else:
        return render_template('map.html', map_data=map_data_dict, user_data=user_data, loggedin=loggedin)

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
        # Verify the token
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)

        # Extract user info from the token
        googleid = idinfo['sub']
        email = idinfo['email']
        name = idinfo['name']

        # Query the database for the user
        user = User.query.filter_by(email=email).first()

        if not user:
            # Insert new user if not found
            user = User(googleid=googleid, email=email, name=name)
            db.session.add(user)
            db.session.commit()

        # Store the user ID in the session
        session['userid'] = user.id

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
    map_name = request.args.get('map')
    map_type = request.args.get('type')
    map_tier = request.args.get('tier')
    sort = request.args.get('sort')

    # Base query
    query = db.session.query(
        Map.map_id,
        Map.name,
        Map.type,
        Map.tier,
        Map.youtube,
        Map.mapper,
        db.func.avg(Rating.rating).label('average_rating'),
        db.func.avg(Rating.tier).label('usertier'),
        db.case(
            (db.func.lower(Map.name).like(db.func.lower(f"%{map_name}%")), 0),
            (db.func.lower(Map.name).like(db.func.lower(f"{map_name}%")), 1),
            (db.func.lower(Map.name).like(db.func.lower(f"%{map_name}")), 2),
            else_=3
        ).label('priority'),
        db.func.strpos(db.func.lower(Map.name), db.func.lower(map_name)).label('name_position') if map_name else db.literal_column('0').label('name_position')
    ).outerjoin(Rating).group_by(
        Map.map_id, Map.name, Map.type, Map.tier, Map.youtube, Map.mapper
    )

    # Filtering
    if map_name:
        query = query.filter(Map.name.ilike(f"%{map_name}%"))
    if map_type:
        query = query.filter(Map.type == map_type)
    if map_tier:
        query = query.filter(Map.tier == map_tier)

    # Sorting
    if sort:
        if sort == "hightier":
            query = query.order_by('priority', Map.tier.desc())
        elif sort == "lowtier":
            query = query.order_by('priority', Map.tier.asc())
        elif sort == "highrate":
            query = query.order_by(
                'priority',
                db.case((db.func.count(Rating.rating) == 0, 0), else_=1).desc(),
                db.desc('average_rating')
            )
        elif sort == "lowrate":
            query = query.order_by(
                'priority',
                db.case((db.func.count(Rating.rating) == 0, 0), else_=1).desc(),
                db.asc('average_rating')
            )
        else:
            query = query.order_by('priority', 'name_position', Map.name)
    else:
        query = query.order_by('priority', 'name_position', Map.name)

    query = query.limit(50)

    results = query.all()

    if is_mobile():
        return render_template('mobilesearch_results.html', query=map_name, search_type=map_type, tier=map_tier, results=results)
    else:
        return render_template('search_results.html', query=map_name, search_type=map_type, tier=map_tier, results=results)

@app.route("/howto")
def howto():
    if is_mobile():
        return render_template('mobilehowto.html')
    else:
        return render_template('howto.html')

@app.route("/request", methods=['GET', 'POST'])
def requestform():
    if is_mobile():
        return render_template('mobilerequestform.html')
    else:
        return render_template('requestform.html')

@app.route("/profile")
def profile():
    if 'userid' not in session:
        return redirect('/')
    
    user_id = session['userid']
    
    # Check if the user has a profile entry
    profile_entry = Profile.query.get(user_id)
    
    if not profile_entry:
        new_profile = Profile(user_id=user_id)
        db.session.add(new_profile)
        db.session.commit()

    # Fetch user profile data
    user_profile = Profile.query.get(user_id)

    # Fetch favorite maps
    favoritemaps = db.session.query(Map.name, db.func.avg(Rating.rating).label('rating')) \
        .join(Rating, Map.map_id == Rating.map_id) \
        .filter(Rating.userid == user_id) \
        .group_by(Map.map_id) \
        .order_by(db.func.avg(Rating.rating).desc()) \
        .limit(10) \
        .all()

    # Fetch total ratings count
    totalratings = db.session.query(db.func.count(Rating.rating)) \
        .filter(Rating.userid == user_id) \
        .scalar()

    return render_template('profile.html', user_profile=user_profile, favoritemaps=favoritemaps, totalratings=totalratings)

@app.route("/editprofile", methods=['GET', 'POST'])
def editprofile():
    if 'userid' not in session:
        return redirect('/')

    user_id = session['userid']
    
    if request.method == 'POST':
        profile = Profile.query.get(user_id)

        if request.form.get('username'):
            profile.username = request.form.get('username')

        if request.form.get('age').isdigit():
            profile.age = int(request.form.get('age'))

        if request.form.get('gender').isdigit():
            gender = int(request.form.get('gender'))
            if 0 <= gender <= 100:
                profile.gender = gender

        db.session.commit()
        return redirect('/profile')
    
    user_profile = Profile.query.get(user_id)
    
    return render_template('editprofile.html', user_profile=user_profile)

@app.route("/profiles/<profileid>", methods=['GET'])
def viewprofile(profileid):
    if profileid.isdigit():
        user_profile = Profile.query.get(profileid)
        if user_profile:
            user_id = user_profile.user_id
            # Fetch favorite maps
            favoritemaps = db.session.query(Map.name, db.func.avg(Rating.rating).label('rating')) \
                .join(Rating, Map.map_id == Rating.map_id) \
                .filter(Rating.userid == user_id) \
                .group_by(Map.map_id) \
                .order_by(db.func.avg(Rating.rating).desc()) \
                .limit(10) \
                .all()

            # Fetch total ratings count
            totalratings = db.session.query(db.func.count(Rating.rating)) \
                .filter(Rating.userid == user_id) \
                .scalar()
            
            if is_mobile():
                return render_template('mobileprofiles.html', user_profile=user_profile, favoritemaps=favoritemaps, totalratings=totalratings)
            else:
                return render_template('profiles.html', user_profile=user_profile, favoritemaps=favoritemaps, totalratings=totalratings)
        else:
            return 'User not found', 404
    else:
        return 'Invalid profile ID', 400

if __name__ == '__main__':
    app.run(debug=True)