#!/usr/bin/env python3
"""
Terminal Project - Web-based Terminal Emulator
Main entry point for the application
"""

import os
import sys
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO

# Configure logging to use stream handler instead of file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Remove FileHandler, use StreamHandler only
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='ui/templates')
app.config['SECRET_KEY'] = 'terminal_project_secret_key'

# Initialize Socket.IO
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode=None,
                   logger=True)

# Add favicon route
@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/')
def index():
    return render_template('index.html')

# Export for Vercel
application = app

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
