import logging

from flask import Flask, abort, g, jsonify, make_response, request, url_for
from flask_cors import CORS

from orca import config
from orca._helpers import import_dict
from orca.app import get_dict, start_search
from orca.model import Search, get_session

log = logging.getLogger(__name__)

flask = Flask(config.app_name)
flask.config.from_object(config.flask)
flask.config["SESSION_REDIS"] = config.db.redis
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
def get_all():
    try:
        return jsonify(get_dict(session=g.session))
    except Exception as e:
        log.exception(f"Error retrieving status: {e}")
        abort(500)


@flask.route("/search", methods=["POST"])
def create_search():
    if not (data := import_dict(request.json)):
        abort(400, "Empty request")
    try:
        if not (search_str := data.get("search_str")):
            abort(400, description="Invalid request")

        search_uid = start_search(search_str)

        response = make_response()
        response.location = url_for("get_search", search_uid=search_uid)
        return response, 202

    except Exception as e:
        log.exception(f"Error submitting new search: {e}")
        abort(500)


@flask.route("/search/<search_uid>", methods=["GET"])
def get_search(search_uid):
    try:
        if not (search := Search.get(search_uid, session=g.session)):
            abort(404, description=f"No search with uid {search_uid}")
        return jsonify(**search.as_dict())
    except Exception as e:
        log.exception(f"Error retrieving search with uid {search_uid}: {e}")
        abort(500)


@flask.route("/search/<search_uid>", methods=["DELETE"])
def delete_search(search_uid):
    try:
        if not (search := Search.get(search_uid, session=g.session)):
            abort(404, description=f"No search with uid {search_uid}")
        search.delete(session=g.session)
        return "", 204
    except Exception as e:
        log.exception(f"Error removing search with uid {search_uid}: {e}")
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
