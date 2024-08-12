from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, abort, g, jsonify, make_response, request, url_for
from flask_cors import CORS

from orca import config, tasks
from orca.db import Document, Search, get_session, redis_client

log = config.get_logger(__name__)
flask = Flask(__name__)
flask_config = config.FLASK(redis_client)
flask.config.from_object(flask_config)
CORS(flask)


@flask.before_request
def before_request():
    g.session = get_session().__enter__()


@flask.teardown_appcontext
def remove_session(exception=None):
    session = g.pop("session", None)
    if session is not None:
        session.__exit__(None, None, None)


@flask.route("/", methods=["GET"])
def api_status():
    try:
        searches = Search.get_all(session=g.session)
        if searches:
            searches = [search.to_dict() for search in searches]
        else:
            searches = []

        return jsonify(
            {
                "version": config.APP_VERSION,
                "total": Document.get_count(session=g.session),
                "searches": searches,
                "created": f"{datetime.now(ZoneInfo('UTC')).isoformat()}",
            }
        )
    except Exception as e:
        log.error(f"Error retrieving status: {e}")
        abort(500, description="Internal server error")


@flask.route("/search", methods=["POST"])
def create_search():
    if not request.json or "search_str" not in request.json:
        abort(400, description='Invalid request, missing "search_str" field')
    try:
        search_str = request.json["search_str"]
        if search_str == "":
            abort(400, description='Invalid request, "search_str" field left blank')

        # Add search to database
        search = Search.create(
            search_str,
            session=g.session,
        )
        if not search:
            abort(500, description="Internal server error")

        # Start processing
        tasks.start_search(search.id)

        # Return with status and location
        response = make_response(
            jsonify(
                {
                    "status": "STARTED",
                    "search_id": search.id,
                }
            ),
            201,
        )
        response.headers["Location"] = url_for("get_search", search_id=search.id)
        return response

    except Exception as e:
        log.error(f"Error submitting new search: {e}")
        abort(500, description="Internal server error")


@flask.route("/search/<search_id>", methods=["GET"])
def get_search(search_id):
    try:
        search = Search.get(search_id, session=g.session)
        if not search:
            abort(404, description=f"No search with id {search_id}")
        return jsonify(search)
    except Exception as e:
        log.error(f"Error retreiving search with id {search_id}: {e}")
        abort(500, description="Internal server error")


@flask.route("/search/<search_id>", methods=["DELETE"])
def delete_search(search_id):
    try:
        search = Search.get(search_id, session=g.session)
        if not search:
            abort(404, description=f"No search with id {search_id}")
        search.delete(session=g.session)
        return "", 204
    except Exception as e:
        log.error(f"Error removing search with id {search_id}: {e}")
        abort(500, description="Internal server error")


@flask.errorhandler(400)
def bad_request(error):
    return jsonify({"error": f"{error.description}"}), 400


@flask.errorhandler(404)
def not_found(error):
    return jsonify({"error": f"{error.description}"}), 404


@flask.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error": f"{error.description}"}), 500


if __name__ == "__main__":
    flask.run()
