from datetime import datetime
from flask_wtf import Form
from wtforms import StringField, SelectField, SelectMultipleField, DateTimeField, BooleanField
from wtforms.validators import DataRequired, AnyOf, URL, Optional, ValidationError, Regexp
from models import Artist, Venue

# The following Regular Expression should allow for MOST valid phone numbers:
# Note: Area code cannot start with a 0 or 1
#       Prefix cannot start with a 0 or 1
# see: https://stackoverflow.com/questions/123559/how-to-validate-phone-numbers-using-regex

VALID_PHONE_NUMBER_REGEX = "^(?:(?:\+?1\s*(?:[.-]\s*)?)?(?:\(\s*([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9])\s*\)|([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9]))\s*(?:[.-]\s*)?)?([2-9]1[02-9]|[2-9][02-9]1|[2-9][02-9]{2})\s*(?:[.-]\s*)?([0-9]{4})(?:\s*(?:#|x\.?|ext\.?|extension)\s*(\d+))?$"

VALID_GENRES = [
    "Alternative",
    "Blues",
    "Classical",
    "Country",
    "Electronic",
    "Folk",
    "Funk",
    "Hip-Hop",
    "Heavy Metal",
    "Instrumental",
    "Jazz",
    "Musical Theater",
    "Pop",
    "R&B",
    "Reggae",
    "Rock n Roll",
    "Soul",
    "Swing",
    "Other",
]

VALID_STATES = [
    "AL",
    "AZ",
    "AR",
    "CA",
    "AK",
    "CO",
    "CT",
    "DE",
    "DC",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
]


def multi_select_validator(valid_values):
    message = "Invalid value, must be one of: {0}.format(", ".join(valid_values)"

    def _validate(form, field):
        for next_field_value in field.data:
            if next_field_value not in valid_values:
                raise ValidationError(message)

    return _validate


def artist_id_validator(form, field):
    # First ensure that the incoming value is an integer
    value = field.data
    try:
        int(value)
    except Exception:
        raise ValidationError("Artist Id must be an Integer")

    num_found = Artist.query.filter_by(id=value).count()
    if num_found == 0:
        raise ValidationError(f"No Artists Found with Id: {value}")


def venue_id_validator(form, field):
    # First ensure that the incoming value is an integer
    value = field.data
    try:
        int(value)
    except Exception:
        raise ValidationError("Venue Id must be an Integer")

    num_found = Venue.query.filter_by(id=value).count()
    if num_found == 0:
        raise ValidationError(f"No Venues Found with Id: {value}")


class ShowForm(Form):
    artist_id = StringField("artist_id", validators=[DataRequired(), artist_id_validator])
    venue_id = StringField("venue_id", validators=[DataRequired(), venue_id_validator])
    start_time = StringField("start_time", validators=[DataRequired()])


class VenueForm(Form):
    name = StringField("name", validators=[DataRequired()])
    city = StringField("city", validators=[DataRequired()])
    state = SelectField(
        "state",
        validators=[DataRequired(), AnyOf(VALID_STATES)],
        choices=[(state, state) for state in VALID_STATES],
    )
    address = StringField("address", validators=[DataRequired()])
    phone = StringField(
        "phone",
        validators=[
            Optional(),
            Regexp(
                VALID_PHONE_NUMBER_REGEX,
                message="Please enter a valid phone number.",
            ),
        ],
    )
    image_link = StringField("image_link", validators=[Optional(), URL()])

    genres = SelectMultipleField(
        "genres",
        validators=[DataRequired(), multi_select_validator(VALID_GENRES)],
        choices=[(genre, genre) for genre in VALID_GENRES],
    )
    facebook_link = StringField(
        # TODO implement enum restriction
        "facebook_link",
        validators=[Optional(), URL()],
    )

    website = StringField("website", validators=[Optional(), URL()])

    seeking_talent = BooleanField("seeking_talent")

    seeking_description = StringField("seeking_description")


class ArtistForm(Form):
    name = StringField("name", validators=[DataRequired()])
    city = StringField("city", validators=[DataRequired()])
    state = SelectField(
        "state",
        validators=[DataRequired(), AnyOf(VALID_STATES)],
        choices=[(state, state) for state in VALID_STATES],
    )
    phone = StringField(
        "phone",
        validators=[
            Optional(),
            Regexp(
                VALID_PHONE_NUMBER_REGEX,
                message="Please enter a valid phone number.",
            ),
        ],
    )
    image_link = StringField("image_link", validators=[Optional(), URL()])

    genres = SelectMultipleField(
        "genres",
        validators=[DataRequired(), multi_select_validator(VALID_GENRES)],
        choices=[(genre, genre) for genre in VALID_GENRES],
    )
    facebook_link = StringField(
        "facebook_link",
        validators=[Optional(), URL()],
    )

    website = StringField("website", validators=[Optional(), URL()])

    seeking_venue = BooleanField("seeking_venue")

    seeking_description = StringField("seeking_description")
