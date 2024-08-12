import logging

from flask import Flask, abort, g, jsonify, make_response, request, url_for
from flask_cors import CORS

from orca import config
from orca.app import start_search
from orca.model import Corpus, Search, get_redis_client, get_session, get_utcnow

log = logging.getLogger(config.APP_NAME)

r = get_redis_client()

flask = Flask(config.APP_NAME)
flask.config.from_object(config.FlaskConfig)
flask.config["SESSION_REDIS"] = r
CORS(flask)


@flask.before_request
def before_request():
    # Open a new session if we don't already have one
    if "session" not in g:
        g.session = get_session().__enter__()


@flask.after_request
def after_request(response):
    # Add ISO-formatted date header
    timestamp = get_utcnow().isoformat()[:-6] + "Z"
    response.headers["Date-ISO"] = timestamp

    return response


@flask.teardown_request
def teardown_request(exception=None):
    session = g.pop("session", None)
    if session is not None:
        session.__exit__(
            exception.__class__ if exception else None,
            exception,
            exception.__traceback__ if exception else None,
        )


@flask.route("/", methods=["GET"])
def api_status():
    if r.hget("orca:flags", "loading") == b"1":
        abort(503, description="Database is updating, try again later")

    try:
        corpus = Corpus.get_latest(session=g.session).as_dict()
        corpus["documents"] = len(corpus.pop("documents"))
        return jsonify(**corpus)
    except Exception as e:
        log.error(f"Error retrieving status: {e}")
        abort(500)


@flask.route("/search", methods=["POST"])
def create_search():
    if r.hget("orca:flags", "loading") == b"1":
        abort(503, description="Database is updating, try again later")

    if not request.json or "search_str" not in request.json:
        abort(400, description='Invalid request, missing "search_str" field')
    try:
        search_str = request.json["search_str"]
        if search_str == "":
            abort(400, description='Invalid request, "search_str" field left blank')

        search_id = start_search(search_str)

        # Return with status and location
        response = make_response()
        response.location = url_for("get_search", search_id=search_id)
        return response, 202

    except Exception as e:
        log.error(f"Error submitting new search: {e}")
        abort(500)


@flask.route("/search/<search_id>", methods=["GET"])
def get_search(search_id):
    if r.hget("orca:flags", "loading") == b"1":
        abort(503, description="Database is updating, try again later")

    try:
        search = Search.get(search_id, session=g.session)
        if not search:
            abort(404, description=f"No search with id {search_id}")
        return jsonify(**search.as_dict())
    except Exception as e:
        log.error(f"Error retreiving search with id {search_id}: {e}")
        abort(500)


@flask.route("/search/<search_id>", methods=["DELETE"])
def delete_search(search_id):
    if r.hget("orca:flags", "loading") == b"1":
        abort(503, description="Database is updating, try again later")

    try:
        search = Search.get(search_id, session=g.session)
        if not search:
            abort(404, description=f"No search with id {search_id}")
        search.delete(session=g.session)
        return "", 204
    except Exception as e:
        log.error(f"Error removing search with id {search_id}: {e}")
        abort(500)


@flask.route("/log")
def get_log():
    if config.LOG_OPEN:
        try:
            with config.LOG_FILE.open() as f:
                content = [ln.strip() for ln in f.readlines()]
            response = make_response("\n".join(content[-40:]))
            response.content_type = "text/plain; charset=utf-8"
            return response
        except Exception as e:
            log.error(f"Error retrieving logs: {e}")
            abort(500)
    else:
        abort(404)


@flask.errorhandler(400)
def bad_request(error):
    return jsonify(error=error.description), 400


@flask.errorhandler(404)
def not_found(error):
    return jsonify(error=error.description), 404


@flask.errorhandler(500)
def internal_server_error(error):
    return jsonify(error=error.description), 500
