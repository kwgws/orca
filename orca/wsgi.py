import logging

from flask import Flask, abort, g, jsonify, make_response, request, url_for
from flask_cors import CORS

from orca import _config
from orca.app import get_overview, start_search
from orca.model import Search, get_redis_client, get_session

log = logging.getLogger(__name__)
r = get_redis_client()

flask = Flask(_config.APP_NAME)
flask.config.from_object(_config.FlaskConfig)
flask.config["SESSION_REDIS"] = r
CORS(flask)


@flask.before_request
def before_request():
    # Open a new session if we don't already have one
    if "session" not in g:
        g.session = get_session().__enter__()


@flask.teardown_request
def teardown_request(exception=None):
    if session := g.pop("session", None):
        session.__exit__(
            exception.__class__ if exception else None,
            exception,
            exception.__traceback__ if exception else None,
        )


@flask.route("/", methods=["GET"])
def index():
    if r.hget("orca:flags", "loading") == b"1":
        abort(503, description="Database is updating, try again later")
    try:
        return jsonify(get_overview(session=g.session))
    except Exception as e:
        log.exception(f"Error retrieving status: {e}")
        abort(500)


@flask.route("/search", methods=["POST"])
def create_search():
    if r.hget("orca:flags", "loading") == b"1":
        abort(503, description="Database is updating, try again later")

    if not request.json or "search_str" not in request.json:
        abort(400, description='Invalid request, missing "search_str" field')
    try:
        if search_str := request.json.get("search_str"):
            abort(400, description='Invalid request, "search_str" field left blank')

        search_uid = start_search(search_str)

        # Return with status and location
        response = make_response()
        response.location = url_for("get_search", search_uid=search_uid)
        return response, 202

    except Exception as e:
        log.exception(f"Error submitting new search: {e}")
        abort(500)


@flask.route("/search/<search_uid>", methods=["GET"])
def get_search(search_uid):
    if r.hget("orca:flags", "loading") == b"1":
        abort(503, description="Database is updating, try again later")

    try:
        if not (search := Search.get(search_uid, session=g.session)):
            abort(404, description=f"No search with uid {search_uid}")
        return jsonify(**search.as_dict())
    except Exception as e:
        log.exception(f"Error retrieving search with uid {search_uid}: {e}")
        abort(500)


@flask.route("/search/<search_uid>", methods=["DELETE"])
def delete_search(search_uid):
    if r.hget("orca:flags", "loading") == b"1":
        abort(503, description="Database is updating, try again later")

    try:
        if not (search := Search.get(search_uid, session=g.session)):
            abort(404, description=f"No search with uid {search_uid}")
        search.delete(session=g.session)
        return "", 204
    except Exception as e:
        log.exception(f"Error removing search with uid {search_uid}: {e}")
        abort(500)


@flask.route("/log")
def get_log():
    try:
        response = make_response(_config.LOG_FILE.read_text())
        response.content_type = "text/plain; charset=utf-8"
        return response
    except Exception as e:
        log.exception(f"Error retrieving logs: {e}")
        abort(500)


@flask.errorhandler(400)
def bad_request(error):
    return jsonify(error=error.description), 400


@flask.errorhandler(404)
def not_found(error):
    return jsonify(error=error.description), 404


@flask.errorhandler(500)
def internal_server_error(error):
    return jsonify(error=error.description), 500


@flask.errorhandler(503)
def busy_error(error):
    return jsonify(error=error.description), 503
