from flask import Flask, jsonify, request, g
from supabase import create_client, Client
from api.v1.views import app_views
from api.v1.config import Config
from flask_cors import CORS
from os import getenv
from dotenv import load_dotenv
from api.v1.auth import load_user_from_jwt, init_supabase_clients, public_supabase_client, service_supabase_client
import logging



logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s %(name)s %(threadName)s - %(message)s')
app = Flask(__name__)
app.config.from_object(Config)
CORS(app, supports_credentials=True)
app.url_map.strict_slashes = False 
app.register_blueprint(app_views)
app.before_request(load_user_from_jwt)


# Initialize Supabase clients (will be done via init_supabase_clients)
with app.app_context():
    init_supabase_clients(app)


# --- Health Check Route ---
@app.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    return jsonify({"status": "ok", "message": "Service is running!"}), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(401)
def unauthorised(error) -> str:
    """
    unauthorised handler
    """
    return jsonify({"error": "Unauthorized"}), 401


@app.errorhandler(403)
def handle_forbidden(error) -> str:
    """
    forbidden handler
    """
    return jsonify({"error": "Forbidden"}), 403

@app.errorhandler(500)
def internal_server_error(error) -> str:
    """
    internal server error handler
    """
    return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    host = getenv('FLASK_HOST', '0.0.0.0')
    port = getenv('FLASK_PORT', 5000)
    app.run(debug=True, port=port, host=host) # Run on port 5000 for development