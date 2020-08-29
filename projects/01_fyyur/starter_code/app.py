# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf.csrf import CSRFProtect
from forms import ArtistForm, VenueForm, ShowForm
from sqlalchemy.exc import IntegrityError
import datetime
from models import db, Artist, Venue, Show
from sqlalchemy import or_

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object("config")
db.init_app(app)
csrf = CSRFProtect(app)
migrate = Migrate(app, db)
# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


# This is one of the issues that many folks were having in the Knowledge Base - I'm not sure
# if anyone really understands this at the Knowledge Base, but this jinja filter is what is
# 'formatting' the show_times in all the templates . . .
# Since we are storing a db.DateTime object, a simple check of the incoming value
# is a nice way to allow things to work no matter what gets sent in . . .
def format_datetime(value, format="medium"):
    if type(value) == str:
        date = dateutil.parser.parse(value)
    else:
        date = value
    if format == "full":
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == "medium":
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters["datetime"] = format_datetime

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route("/")
def index():
    return render_template("pages/home.html")


#  ----------------------------------------------------------------
#  Venues
#  ----------------------------------------------------------------


@app.route("/venues")
def venues():
    areas = [
        unique_citystate for unique_citystate in Venue.query.distinct(Venue.city, Venue.state).all()
    ]
    data = []
    for area in areas:
        venues = Venue.query.filter(Venue.city == area.city, Venue.state == area.state).all()
        data.append(
            {
                "city": area.city,
                "state": area.state,
                "venues": venues,
            }
        )
    return render_template("pages/venues.html", areas=data)


@csrf.exempt
@app.route("/venues/search", methods=["POST"])
def search_venues():
    # seach for Hop should return "The Musical Hop".
    # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
    search_term = request.form.get("search_term", "")

    # Allow user to enter wildcard (asterisks) in the search input
    # We'll convert to the internal percent sign - this will allow
    # Users to search for multiple substrings at once . . .
    results_from_db = Venue.query.filter(
        Venue.name.ilike(f"%{search_term.replace('*', '%')}%")
    ).all()

    display_results = []
    for next_db_result in results_from_db:
        display_results.append(
            {
                "id": next_db_result.id,
                "name": next_db_result.name,
            }
        )

    response = {
        "count": len(display_results),
        "data": display_results,
    }
    return render_template(
        "pages/search_venues.html",
        results=response,
        search_term=search_term,
    )


@app.route("/venues/<int:venue_id>")
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    venue = Venue.query.filter_by(id=venue_id).first_or_404()
    data = {key: value for key, value in venue.__dict__.items()}
    shows = venue.shows
    data["upcoming_shows"] = [
        {
            "start_time": show.start_time,
            "artist_image_link": show.artist.image_link,
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
        }
        for show in shows
        if show.start_time > datetime.datetime.now()
    ]
    data["upcoming_shows_count"] = len(data["upcoming_shows"])
    data["past_shows"] = [
        {
            "start_time": show.start_time,
            "artist_image_link": show.artist.image_link,
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
        }
        for show in shows
        if show.start_time < datetime.datetime.now()
    ]
    data["past_shows_count"] = len(data["past_shows"])
    return render_template("pages/show_venue.html", venue=data)


@app.route("/venues/create", methods=["GET"])
def create_venue_form():
    form = VenueForm()
    return render_template("forms/new_venue.html", form=form)


@app.route("/venues/create", methods=["POST"])
def create_venue_submission():
    venueForm = VenueForm(request.form)
    newVenueId = None
    if venueForm.validate():
        try:
            newVenue = Venue()
            newVenue.name = venueForm.name.data
            newVenue.address = venueForm.address.data
            newVenue.city = venueForm.city.data
            newVenue.state = venueForm.state.data
            newVenue.phone = venueForm.phone.data
            newVenue.website = venueForm.website.data
            newVenue.facebook_link = venueForm.facebook_link.data
            newVenue.seeking_talent = venueForm.seeking_talent.data
            newVenue.seeking_description = venueForm.seeking_description.data
            newVenue.image_link = venueForm.image_link.data
            newVenue.genres = venueForm.genres.data
            db.session.add(newVenue)
            db.session.commit()
            newVenueId = newVenue.id
            flash(f"Venue {newVenue.name} was successfully listed.")
        except IntegrityError as ie:
            db.session.rollback()
            original_exception = ie.orig
            if "already exists" in str(original_exception):
                error_message = f"A venue with name {newVenue.name} is already listed."
            else:
                error_message = f"Unexpected error occurred: {str(ie.orig)}"
            flash(
                f"Error: {error_message}",
                "error",
            )
            return render_template("forms/new_venue.html", form=venueForm, venue=newVenue)
        except Exception as exc:
            db.session.rollback()
            flash(
                f"Error: unexpected problem when attempting to create Venue {newVenue.name}: {str(exc)}",
                "error",
            )
            return render_template("forms/new_venue.html", form=venueForm, venue=newVenue)
    else:
        for field, errors in venueForm.errors.items():
            flash(f"Error in field {venueForm[field].label.text}: {errors}", "error")
        return render_template("forms/new_venue.html", form=venueForm)

    return redirect(url_for("show_venue", venue_id=newVenueId))


@app.route("/venues/<venue_id>", methods=["DELETE"])
def delete_venue(venue_id):
    try:
        venue = Venue.query.filter_by(id=venue_id).first_or_404()
        db.session.delete(venue)
        db.session.commit()
    except Exception:
        db.session.rollback()
    finally:
        db.session.close()
    return jsonify({"success": True})

    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage


@app.route("/venues/<int:venue_id>/edit", methods=["GET"])
def edit_venue(venue_id):
    venue = Venue.query.filter_by(id=venue_id).first_or_404()
    form = VenueForm(obj=venue)
    return render_template("forms/edit_venue.html", form=form, venue=venue)


@app.route("/venues/<int:venue_id>/edit", methods=["POST"])
def edit_venue_submission(venue_id):
    venue = Venue.query.filter_by(id=venue_id).first_or_404()
    venueForm = VenueForm(request.form)

    if venueForm.validate():
        try:
            venue.name = venueForm.name.data
            venue.city = venueForm.city.data
            venue.state = venueForm.state.data
            venue.address = venueForm.address.data
            venue.phone = venueForm.phone.data
            venue.genres = venueForm.genres.data
            venue.website = venueForm.website.data
            venue.facebook_link = venueForm.facebook_link.data
            venue.seeking_talent = venueForm.seeking_talent.data
            venue.seeking_description = venueForm.seeking_description.data
            venue.image_link = venueForm.image_link.data
            db.session.commit()
            flash(f"Venue {venue.name} was successfully updated.")
        except ValueError:
            db.session.rollback()
            flash(
                f"Error: unexpected problem when attempting to modify Venue {venue.name}", "error"
            )
    else:
        for field, errors in venueForm.errors.items():
            flash(f"Error in field {venueForm[field].label.text}: {errors}", "error")
        return render_template("forms/edit_venue.html", form=venueForm, venue=venue)

    return redirect(url_for("show_venue", venue_id=venue_id))


#  ----------------------------------------------------------------
#  Artists
#  ----------------------------------------------------------------


@app.route("/artists")
def artists():
    data = Artist.query.order_by("id").all()
    return render_template("pages/artists.html", artists=data)


@app.route("/artists/<int:artist_id>", methods=["DELETE"])
def delete_artist(artist_id):
    try:
        artist = Artist.query.filter_by(id=artist_id).first_or_404()
        artistName = artist.name
        db.session.delete(artist)
        db.session.commit()
        flash(f"Artist {artistName} was successfully deleted!")
    except Exception as exc:
        db.session.rollback()
        flash(f"Unable to delete Artist {artistName}: {str(exc)}", "error")
    finally:
        db.session.close()

    return jsonify({"success": True})


@csrf.exempt
@app.route("/artists/search", methods=["POST"])
def search_artists():
    # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
    # search for "band" should return "The Wild Sax Band".
    search_term = request.form.get("search_term", "")

    # Allow user to enter wildcard (asterisks) in the search input
    # We'll convert to the internal percent sign - this will allow
    # Users to search for multiple substrings at once . . .
    results_from_db = Artist.query.filter(
        Artist.name.ilike(f"%{search_term.replace('*', '%')}%")
    ).all()

    display_results = []
    for next_db_result in results_from_db:
        display_results.append(
            {
                "id": next_db_result.id,
                "name": next_db_result.name,
            }
        )

    response = {
        "count": len(display_results),
        "data": display_results,
    }
    return render_template(
        "pages/search_artists.html",
        results=response,
        search_term=search_term,
    )


@app.route("/artists/<int:artist_id>", methods=["GET"])
def show_artist(artist_id):
    artist = Artist.query.filter_by(id=artist_id).first_or_404()
    data = {key: value for key, value in artist.__dict__.items()}
    shows = artist.shows
    data["upcoming_shows"] = [
        {
            "start_time": show.start_time,
            "venue_image_link": show.venue.image_link,
            "venue_id": show.venue.id,
            "venue_name": show.venue.name,
        }
        for show in shows
        if show.start_time > datetime.datetime.now()
    ]
    data["upcoming_shows_count"] = len(data["upcoming_shows"])
    data["past_shows"] = [
        {
            "start_time": show.start_time,
            "venue_image_link": show.venue.image_link,
            "venue_id": show.venue.id,
            "venue_name": show.venue.name,
        }
        for show in shows
        if show.start_time < datetime.datetime.now()
    ]
    data["past_shows_count"] = len(data["past_shows"])
    return render_template("pages/show_artist.html", artist=data)


@app.route("/artists/<int:artist_id>/edit", methods=["GET"])
def edit_artist(artist_id):
    artist = Artist.query.filter_by(id=artist_id).first_or_404()
    form = ArtistForm(obj=artist)
    return render_template("forms/edit_artist.html", form=form, artist=artist)


@app.route("/artists/<int:artist_id>/edit", methods=["POST"])
def edit_artist_submission(artist_id):
    artist = Artist.query.filter_by(id=artist_id).first_or_404()
    artistForm = ArtistForm(request.form)

    if artistForm.validate():
        try:
            artist.name = artistForm.name.data
            artist.city = artistForm.city.data
            artist.state = artistForm.state.data
            artist.phone = artistForm.phone.data
            artist.genres = artistForm.genres.data
            artist.website = artistForm.website.data
            artist.facebook_link = artistForm.facebook_link.data
            artist.seeking_venue = artistForm.seeking_venue.data
            artist.seeking_description = artistForm.seeking_description.data
            artist.image_link = artistForm.image_link.data
            db.session.commit()
            flash(f"Artist {artist.name} was successfully updated.")
        except ValueError:
            db.session.rollback()
            flash(
                f"Error: unexpected problem when attempting to modify Artist {artist.name}", "error"
            )
    else:
        for field, errors in artistForm.errors.items():
            flash(f"Error in field {artistForm[field].label.text}: {errors}", "error")
        return render_template("forms/edit_artist.html", form=artistForm, artist=artist)

    return redirect(url_for("show_artist", artist_id=artist_id))


@app.route("/artists/create", methods=["GET"])
def create_artist_form():
    form = ArtistForm()
    return render_template("forms/new_artist.html", form=form)


@app.route("/artists/create", methods=["POST"])
def create_artist_submission():
    artistForm = ArtistForm(request.form)
    newArtistId = None
    if artistForm.validate():
        try:
            newArtist = Artist()
            newArtist.name = artistForm.name.data
            newArtist.city = artistForm.city.data
            newArtist.state = artistForm.state.data
            newArtist.phone = artistForm.phone.data
            newArtist.genres = artistForm.genres.data
            newArtist.website = artistForm.website.data
            newArtist.facebook_link = artistForm.facebook_link.data
            newArtist.seeking_venue = artistForm.seeking_venue.data
            newArtist.seeking_description = artistForm.seeking_description.data
            newArtist.image_link = artistForm.image_link.data
            db.session.add(newArtist)
            db.session.commit()
            newArtistId = newArtist.id
            flash(f"Artist {newArtist.name} was successfully listed.")
        except IntegrityError as ie:
            db.session.rollback()
            original_exception = ie.orig
            if "already exists" in str(original_exception):
                error_message = f"An artist with name {newArtist.name} is already listed."
            else:
                error_message = f"Unexpected error occurred: {str(ie.orig)}"
            flash(
                f"Error: {error_message}",
                "error",
            )
            return render_template("forms/new_artist.html", form=artistForm, artist=newArtist)
        except Exception as exc:
            db.session.rollback()
            flash(
                f"Error: unexpected problem when attempting to create Artist {newArtist.name}: {str(exc)}",
                "error",
            )
            return render_template("forms/new_artist.html", form=artistForm, artist=newArtist)
    else:
        for field, errors in artistForm.errors.items():
            flash(f"Error in field {artistForm[field].label.text}: {errors}", "error")
        return render_template("forms/new_artist.html", form=artistForm)

    return redirect(url_for("show_artist", artist_id=newArtistId))


#  Shows
#  ----------------------------------------------------------------


@app.route("/shows")
def shows():
    # displays list of shows at /shows
    shows = Show.query.order_by("id").all()
    data = [
        {
            "venue_id": show.venue.id,
            "venue_name": show.venue.name,
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": show.start_time,
        }
        for show in shows
    ]
    return render_template("pages/shows.html", shows=data)


@app.route("/shows/create")
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template("forms/new_show.html", form=form)


@app.route("/shows/create", methods=["POST"])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    showForm = ShowForm(request.form)
    if showForm.validate():
        try:
            newShow = Show()
            newShow.artist_id = showForm.artist_id.data
            newShow.venue_id = showForm.venue_id.data
            newShow.start_time = showForm.start_time.data
            db.session.add(newShow)
            db.session.commit()

            flash("Show was successfully listed.")
        except IntegrityError as ie:
            db.session.rollback()
            error_message = f"Unexpected error occurred: {str(ie.orig)}"
            flash(
                f"Error: {error_message}",
                "error",
            )
            return render_template("forms/new_show.html", form=showForm, show=newShow)
        except Exception as exc:
            db.session.rollback()
            flash(
                f"Error: unexpected problem when attempting to list Show: {str(exc)}",
                "error",
            )
            return render_template("forms/new_show.html", form=showForm, show=newShow)
    else:
        for field, errors in showForm.errors.items():
            flash(f"Error in field {showForm[field].label.text}: {errors}", "error")
        return render_template("forms/new_show.html", form=showForm)

    return redirect(url_for("shows"))


@csrf.exempt
@app.route("/shows/search", methods=["POST"])
def search_shows():
    # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
    # search for "band" should return "The Wild Sax Band".
    search_term = request.form.get("search_term", "")

    # Allow user to enter wildcard (asterisks) in the search input
    # We'll convert to the internal percent sign - this will allow
    # Users to search for multiple substrings at once . . .
    search_for = search_term.replace("*", "%")
    shows = (
        Show.query.join(Artist, Show.artist_id == Artist.id)
        .join(Venue, Show.venue_id == Venue.id)
        .filter(Venue.name.ilike(f"%{search_for}%") | Artist.name.ilike(f"%{search_for}%"))
        .all()
    )

    data = {}
    data["upcoming_shows"] = [
        {
            "start_time": show.start_time,
            "venue_image_link": show.venue.image_link,
            "venue_id": show.venue.id,
            "venue_name": show.venue.name,
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
        }
        for show in shows
        if show.start_time > datetime.datetime.now()
    ]
    data["upcoming_shows_count"] = len(data["upcoming_shows"])
    data["past_shows"] = [
        {
            "start_time": show.start_time,
            "venue_image_link": show.venue.image_link,
            "venue_id": show.venue.id,
            "venue_name": show.venue.name,
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
        }
        for show in shows
        if show.start_time < datetime.datetime.now()
    ]
    data["past_shows_count"] = len(data["past_shows"])

    return render_template(
        "pages/search_shows.html",
        results=data,
        search_term=search_term,
    )


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


def load_seed_data_if_needed():
    # If we have an empty database, load initial data
    with app.app_context():
        # Load seed data for Venues if there are no Venues at startup
        if db.session.query(Venue).count() == 0:
            print("")
            print("*" * 80)
            print("Database contains no Venues - loading seed data . . .")
            print("*" * 80)
            seed_venues_data = [
                {
                    "name": "The Musical Hop",
                    "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
                    "address": "1015 Folsom Street",
                    "city": "San Francisco",
                    "state": "CA",
                    "phone": "321-323-1234",
                    "website": "https://www.themusicalhop.com",
                    "facebook_link": "https://www.facebook.com/TheMusicalHop",
                    "seeking_talent": True,
                    "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
                    "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60",
                },
                {
                    "name": "The Dueling Pianos Bar",
                    "genres": ["Classical", "R&B", "Hip-Hop"],
                    "address": "335 Delancey Street",
                    "city": "New York",
                    "state": "NY",
                    "phone": "914-203-1132",
                    "website": "https://www.theduelingpianos.com",
                    "facebook_link": "https://www.facebook.com/theduelingpianos",
                    "seeking_talent": False,
                    "image_link": "https://images.unsplash.com/photo-1497032205916-ac775f0649ae?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=750&q=80",
                },
                {
                    "name": "Park Square Live Music & Coffee",
                    "genres": ["Rock n Roll", "Jazz", "Classical", "Folk"],
                    "address": "34 Whiskey Moore Ave",
                    "city": "San Francisco",
                    "state": "CA",
                    "phone": "415-386-1234",
                    "website": "https://www.parksquarelivemusicandcoffee.com",
                    "facebook_link": "https://www.facebook.com/ParkSquareLiveMusicAndCoffee",
                    "seeking_talent": False,
                    "image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
                },
            ]
            for next_venue_data in seed_venues_data:
                new_venue = Venue()
                new_venue.name = next_venue_data["name"]
                new_venue.city = next_venue_data["city"]
                new_venue.state = next_venue_data["state"]
                new_venue.address = next_venue_data["address"]
                if "phone" in next_venue_data:
                    new_venue.phone = next_venue_data["phone"]
                new_venue.genres = next_venue_data["genres"]
                if "website" in next_venue_data:
                    new_venue.website = next_venue_data["website"]
                if "facebook_link" in next_venue_data:
                    new_venue.facebook_link = next_venue_data["facebook_link"]
                new_venue.seeking_talent = next_venue_data["seeking_talent"]
                if new_venue.seeking_talent:
                    if "seeking_description" in next_venue_data:
                        new_venue.seeking_description = next_venue_data["seeking_description"]
                if "image_link" in next_venue_data:
                    new_venue.image_link = next_venue_data["image_link"]

                db.session.add(new_venue)
                db.session.commit()

        # Load seed data for Artists if there are no Artists at startup
        if db.session.query(Artist).count() == 0:
            print("")
            print("*" * 80)
            print("Database contains no Artists - loading seed data . . .")
            print("*" * 80)
            seed_artists_data = [
                {
                    "name": "Guns N Petals",
                    "genres": ["Rock n Roll"],
                    "city": "San Francisco",
                    "state": "CA",
                    "phone": "326-223-5000",
                    "website": "https://www.gunsnpetalsband.com",
                    "facebook_link": "https://www.facebook.com/GunsNPetals",
                    "seeking_venue": True,
                    "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
                    "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
                },
                {
                    "name": "Matt Quevedo",
                    "genres": ["Jazz"],
                    "city": "New York",
                    "state": "NY",
                    "phone": "300-400-5000",
                    "facebook_link": "https://www.facebook.com/mattquevedo923251523",
                    "seeking_venue": False,
                    "image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
                },
                {
                    "name": "The Wild Sax Band",
                    "genres": ["Jazz", "Classical"],
                    "city": "San Francisco",
                    "state": "CA",
                    "phone": "432-325-5432",
                    "seeking_venue": False,
                    "image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
                },
            ]

            for next_artist_data in seed_artists_data:
                new_artist = Artist()
                new_artist.name = next_artist_data["name"]
                new_artist.city = next_artist_data["city"]
                new_artist.state = next_artist_data["state"]
                if "phone" in next_artist_data:
                    new_artist.phone = next_artist_data["phone"]
                new_artist.genres = next_artist_data["genres"]
                if "website" in next_artist_data:
                    new_artist.website = next_artist_data["website"]
                if "facebook_link" in next_artist_data:
                    new_artist.facebook_link = next_artist_data["facebook_link"]
                new_artist.seeking_venue = next_artist_data["seeking_venue"]
                if new_artist.seeking_venue:
                    if "seeking_description" in next_artist_data:
                        new_artist.seeking_description = next_artist_data["seeking_description"]
                if "image_link" in next_artist_data:
                    new_artist.image_link = next_artist_data["image_link"]

                db.session.add(new_artist)
                db.session.commit()

        if db.session.query(Show).count() == 0:
            print("")
            print("*" * 80)
            print("Database contains no Shows - loading seed data . . .")
            print("*" * 80)
            seed_show_data = [
                {
                    "venue_name": "The Musical Hop",
                    "artist_name": "Guns N Petals",
                    "start_time": "2019-05-21T21:30:00.000Z",
                },
                {
                    "venue_name": "Park Square Live Music & Coffee",
                    "artist_name": "Matt Quevedo",
                    "start_time": "2019-06-15T23:00:00.000Z",
                },
                {
                    "venue_name": "Park Square Live Music & Coffee",
                    "artist_name": "The Wild Sax Band",
                    "start_time": "2035-04-01T20:00:00.000Z",
                },
                {
                    "venue_name": "Park Square Live Music & Coffee",
                    "artist_name": "The Wild Sax Band",
                    "start_time": "2035-04-08T20:00:00.000Z",
                },
                {
                    "venue_name": "Park Square Live Music & Coffee",
                    "artist_name": "The Wild Sax Band",
                    "start_time": "2035-04-15T20:00:00.000Z",
                },
            ]

            for next_show_data in seed_show_data:
                artist = Artist.query.filter_by(name=next_show_data["artist_name"]).first()
                venue = Venue.query.filter_by(name=next_show_data["venue_name"]).first()
                newShow = Show()
                newShow.artist_id = artist.id
                newShow.venue_id = venue.id
                newShow.start_time = dateutil.parser.parse(next_show_data["start_time"])
                db.session.add(newShow)
                db.session.commit()


if not app.debug:
    file_handler = FileHandler("error.log")
    file_handler.setFormatter(
        Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info("errors")

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == "__main__":
    load_seed_data_if_needed()
    app.run()

# Or specify port manually:
"""
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
"""
