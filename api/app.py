from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from uuid import uuid4
from chat import ask_question
import os
import sys
import jwt
import datetime
import requests

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

@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.get_json()
    trace_id = data.get('trace_id')
    value = data.get('value')  # 1 for 👍, -1 for 👎
    
    if not trace_id or value is None:
        return jsonify({"success": False, "error": "Missing trace_id or value"}), 400
    
    # Log feedback locally first
    app.logger.info(f"User feedback: trace_id={trace_id}, value={value} ({'positive' if value > 0 else 'negative'})")
    
    # Try to send to Portkey
    try:
        response = requests.post(
            'https://api.portkey.ai/v1/feedback',
            headers={
                'x-portkey-api-key': os.getenv("PORTKEY_API_KEY"),
                'Content-Type': 'application/json'
            },
            json={
                'trace_id': trace_id,
                'value': value
            },
            timeout=5
        )
        
        if response.status_code == 200:
            app.logger.info(f"Feedback sent to Portkey successfully: trace_id={trace_id}")
        else:
            app.logger.warning(f"Portkey feedback API returned {response.status_code}: {response.text}")
    except Exception as e:
        app.logger.warning(f"Failed to send feedback to Portkey: {str(e)}")
    
    return jsonify({"success": True})


@app.cli.command()
def create_index():
    """Create or re-create the Elasticsearch index."""
    basedir = os.path.abspath(os.path.dirname(__file__))
    sys.path.append(f"{basedir}/../")

    from data import index_data

    index_data.main()


# if __name__ == "__main__":
#     app.run(port=3001, debug=True, host='0.0.0.0')
