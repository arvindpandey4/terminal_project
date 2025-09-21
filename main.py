#!/usr/bin/env python3
"""
Terminal Project - Web-based Terminal Emulator
Main entry point for the application
"""

import os
import sys
import json
import logging
import eventlet
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO
import psutil

# Patch sockets to be non-blocking
eventlet.monkey_patch()

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import project modules
from commands import command_handler
from utils import system_monitor, nlp_interpreter, history_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'terminal.log'))
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='ui/templates')
app.config['SECRET_KEY'] = 'terminal_project_secret_key'

# Initialize Socket.IO with async mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Current working directory for terminal commands (per tab)
TAB_DIRECTORIES = {}
DEFAULT_DIR = os.path.expanduser("~")

def get_tab_directory(tab_id):
    """Get the current directory for a tab, or create it if it doesn't exist."""
    if tab_id not in TAB_DIRECTORIES:
        TAB_DIRECTORIES[tab_id] = DEFAULT_DIR
    return TAB_DIRECTORIES[tab_id]

@app.route('/')
def index():
    """Render the main terminal interface."""
    return render_template('index.html')

@app.route('/api/system-info')
def system_info():
    """Get system information for the dashboard."""
    return jsonify({
        'cpu': system_monitor.get_cpu_usage(),
        'memory': system_monitor.get_memory_usage(),
        'processes': system_monitor.get_process_count()
    })

@app.route('/api/export-logs', methods=['GET'])
def export_logs():
    """Export command history and outputs as a file."""
    try:
        format_type = request.args.get('format', 'txt')
        history_data = history_manager.get_full_history()
        
        if format_type == 'md':
            filename = 'terminal_history.md'
            content = history_manager.format_history_markdown(history_data)
        else:
            filename = 'terminal_history.txt'
            content = history_manager.format_history_text(history_data)
        
        # Create temporary file and return it
        temp_dir = os.path.join(app.static_folder, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, filename)
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return send_from_directory(temp_dir, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error exporting logs: {str(e)}")
        return jsonify({"error": str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected")
    # Send initial system information
    socketio.emit('system_info', {
        'cpu': system_monitor.get_cpu_usage(),
        'memory': system_monitor.get_memory_usage(),
        'processes': system_monitor.get_process_count()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info('Client disconnected')

@socketio.on('command')
def handle_command(data):
    """Handle incoming command from client."""
    try:
        command = data.get('command', '').strip()
        tab_id = data.get('tab_id', 'default')
        current_dir = get_tab_directory(tab_id)
        
        # Execute command
        result = command_handler.execute_command(command, current_dir)
        
        # Update directory if changed
        if result.get('new_dir'):
            TAB_DIRECTORIES[tab_id] = result['new_dir']
        
        # Emit result back to client
        socketio.emit('output', {
            'output': result['output'],
            'tab_id': tab_id
        })
        
        # Add to history
        history_manager.add_command(command, tab_id)
        
    except Exception as e:
        logger.error(f"Error handling command: {str(e)}")
        socketio.emit('output', {
            'output': f"Error: {str(e)}",
            'tab_id': tab_id
        })

@socketio.on('autocomplete')
def handle_autocomplete(data):
    """Handle command autocomplete requests."""
    partial_command = data.get('command', '')
    tab_id = data.get('tab_id', 'default')
    
    current_dir = get_tab_directory(tab_id)
    suggestions = command_handler.get_autocomplete_suggestions(partial_command, current_dir)
    socketio.emit('autocomplete_suggestions', {
        'suggestions': suggestions,
        'tab_id': tab_id
    })

@socketio.on('get_history')
def handle_get_history(data):
    """Retrieve command history for a tab."""
    tab_id = data.get('tab_id', 'default')
    history = history_manager.get_history(tab_id)
    socketio.emit('history', {
        'history': history,
        'tab_id': tab_id
    })

def start_system_monitor():
    """Start the system monitoring background thread."""
    def emit_system_info():
        while True:
            try:
                socketio.sleep(2)  # Update every 2 seconds
                socketio.emit('system_info', {
                    'cpu': system_monitor.get_cpu_usage(),
                    'memory': system_monitor.get_memory_usage(),
                    'processes': system_monitor.get_process_count()
                })
            except Exception as e:
                logger.error(f"Error in system monitor: {str(e)}")
    
    socketio.start_background_task(emit_system_info)

# Export the app for Vercel
application = app

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
