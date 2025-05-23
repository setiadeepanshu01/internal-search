from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from uuid import uuid4
from chat import ask_question
import os
import sys
import jwt
import datetime

app = Flask(__name__, static_folder="../frontend/build", static_url_path="/")
CORS(app)

SECRET_KEY = os.environ.get('SECRET_KEY')
AUTH_USERNAME = os.environ.get('AUTH_USERNAME')
AUTH_PASSWORD = os.environ.get('AUTH_PASSWORD')

@app.route("/")
def api_index():
    return app.send_static_file("index.html")

@app.route("/api/verify-credentials", methods=["POST"])
def verify_credentials():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username == AUTH_USERNAME and password == AUTH_PASSWORD:
        token = jwt.encode({
            'user': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, SECRET_KEY, algorithm="HS256")
        return jsonify({"authenticated": True, "token": token}), 200
    else:
        return jsonify({"authenticated": False}), 401

@app.route("/api/chat", methods=["POST"])
def api_chat():
    request_json = request.get_json()
    question = request_json.get("question")
    if question is None:
        return jsonify({"msg": "Missing question from request JSON"}), 400

    session_id = request.args.get("session_id", str(uuid4()))
    return Response(ask_question(question, session_id), mimetype="text/event-stream")


@app.cli.command()
def create_index():
    """Create or re-create the Elasticsearch index."""
    basedir = os.path.abspath(os.path.dirname(__file__))
    sys.path.append(f"{basedir}/../")

    from data import index_data

    index_data.main()


# if __name__ == "__main__":
#     app.run(port=3001, debug=True, host='0.0.0.0')
