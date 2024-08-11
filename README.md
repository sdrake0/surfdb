SURF DATABASE

Surf DB is a website for viewing and rating surf maps from across a couple different map pools.
Surfing is a game you can play in many different video games, where the goal is to slide along slopes and gain enough speed to reach the finish as fast as possible.
Each map is a different challenge, which is why information about them is useful.
There are a few different websites that have information about surf maps, but some are missing information or maps and all do not embed a video.
My goal is to have one location where you can have all the relevant information about surfing a particular map.
Additionally, I want users to be able to rate the maps they play and let others know what they think of it.

https://www.surfdb.info

Let's go through the app.py:

This is a web application that uses flask, prostgresql, html, css, and jinja.
It uses google authentication to log in, and heroku postgresql database.
I used sqlalchemy as the library from which I am forming queries to execute and display data.
The tables in my database are configured by initializing the database in db.py and modeled in models.py
I have a function is_mobile to check if a user is on a mobile device and display a more mobile friendly template.

Route /:
This is the index page introducing the website. It displays a welcome line, as well as the 10 most rated maps and the 10 highest rated maps.

Route /map/"map_name":
This is a page for every map in the database. Any time a map name is clicked from the index, search page, or profile it leads to this route.
It gathers all the information about the map from the maps table as well as what people have rated it and how difficult people think it is.
If a user is logged in, they are able to submit their own rating and see or change what their previous rating was if they have already rated it.

Route /go-to-map:
This allows for links to be made within the website to go to /map/"map_name".

Route /tokensignin:
This is the login route where new users are put in the database if they haven't logged in before and are logged in.
It verifies that google has accepted their login and stores the session.

Route /logout:
Clears the session, logs the user out.

Route /search:
Upon visiting, the search page produces 50 maps sorted alphabetically and shows a preview of the first result.
When searching, the query prioritizes the searched phrase appearing in the name sooner. I used chatGPT to generate this part.
This was important to have for me, since on other websites if you were to search for "me", thinking of the map "surf_me", the
first map that would appear is "surf_4dimensional" since it is the first in the alphabet that contains "me".
The search also has sorting options and filters. You can filter by map tier and type, and sort by average rating or tier.

Route /howto:
This is small page showing a couple videos that would be helpful to someone who is not experienced with surfing or doesn't know what it is.

Route /profile:
Gives the profile of the user logged in including their highest rated maps and allows them to route to /editprofile to make changes.
Has a copyable text to be able to share your profile.

Route /editprofile:
You can edit your username, age, and gender (slider), and save it. By default all values are none. This allows people who use the same username to not conflict,
since it is based on a profile id rather than username.

Route /profiles/"profileid"
Leads users to a page showing a profile of the user that has that profileid. Includes username, age, gender, maps rated, and 10 favorite maps (highest rated)
