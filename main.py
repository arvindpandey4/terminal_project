#!/usr/bin/env python3
"""
Terminal Project - Web-based Terminal Emulator
Main entry point for the application
"""

import os
import sys
import logging
import signal
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO

# Configure logging - disable all Flask/Werkzeug noise
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)

# Simple print for our messages
def log(message):
    print(f"[TERMINAL] {message}")

# Initialize Flask app
app = Flask(__name__,
           static_folder='static',
           static_url_path='/static',
           template_folder='ui/templates')

app.config['SECRET_KEY'] = 'terminal_project_secret_key'

# Initialize Socket.IO with minimal config
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Export for Vercel (don't overwrite the main app variable)
wsgi_app = app.wsgi_app

# Import project modules after app initialization
from commands import command_handler
from utils import system_monitor, nlp_interpreter, history_manager

# Current working directory for terminal commands (per tab)
TAB_DIRECTORIES = {}
DEFAULT_DIR = os.path.expanduser("~")

def get_tab_directory(tab_id):
    """Get the current directory for a tab, or create it if it doesn't exist."""
    if tab_id not in TAB_DIRECTORIES:
        TAB_DIRECTORIES[tab_id] = DEFAULT_DIR
    return TAB_DIRECTORIES[tab_id]

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    global connected_clients
    connected_clients += 1
    log(f'Client connected (total: {connected_clients})')
    # Send initial system information to dashboard
    socketio.emit('system_info', {
        'cpu': system_monitor.get_cpu_usage(),
        'memory': system_monitor.get_memory_usage(),
        'processes': system_monitor.get_process_count()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    global connected_clients
    connected_clients -= 1
    log(f'Client disconnected (remaining: {connected_clients})')

    # Auto-shutdown when last client disconnects
    if connected_clients <= 0:
        log('Last client disconnected - shutting down server...')
        stop_system_monitor()
        log('Server shutdown complete')
        os._exit(0)  # Force exit since socketio.run() blocks

@socketio.on('command')
def handle_command(data):
    """Process terminal commands."""
    try:
        command = data.get('command', '').strip()
        tab_id = data.get('tab_id', 'default')

        if not command:
            return

        # Get current directory for this tab
        current_dir = get_tab_directory(tab_id)

        # Save command to history
        history_manager.add_command(command, tab_id)

        # Check if it's a natural language command
        if command.startswith('!'):
            # Process natural language command
            nl_command = command[1:].strip()
            try:
                interpreted_commands = nlp_interpreter.interpret(nl_command)

                interpretation_msg = f"Interpreting: {nl_command}\nExecuting: {', '.join(interpreted_commands)}"
                socketio.emit('output', {
                    'output': interpretation_msg,
                    'tab_id': tab_id
                })

                # Execute each interpreted command
                for cmd in interpreted_commands:
                    result = command_handler.execute_command(cmd, current_dir)
                    output_msg = result.get('output', '(no output)')

                    socketio.emit('output', {
                        'output': output_msg,
                        'tab_id': tab_id
                    })

                    if result.get('new_dir'):
                        TAB_DIRECTORIES[tab_id] = result['new_dir']
                        socketio.emit('directory_change', {
                            'directory': TAB_DIRECTORIES[tab_id],
                            'tab_id': tab_id
                        })
                        current_dir = TAB_DIRECTORIES[tab_id]

            except Exception as e:
                socketio.emit('output', {
                    'output': f"Error interpreting command: {str(e)}",
                    'tab_id': tab_id
                })

        else:
            # Process regular command
            try:
                result = command_handler.execute_command(command, current_dir)
                output_msg = result.get('output', '(no output)')

                socketio.emit('output', {
                    'output': str(output_msg),
                    'tab_id': tab_id
                })

                # Update current directory if changed
                if result.get('new_dir'):
                    TAB_DIRECTORIES[tab_id] = result['new_dir']
                    socketio.emit('directory_change', {
                        'directory': TAB_DIRECTORIES[tab_id],
                        'tab_id': tab_id
                    })
            except Exception as cmd_error:
                error_msg = f"Command execution error: {str(cmd_error)}"
                socketio.emit('output', {
                    'output': error_msg,
                    'tab_id': tab_id
                })

    except Exception as e:
        socketio.emit('output', {
            'output': f"Internal error: {str(e)}",
            'tab_id': data.get('tab_id', 'default')
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

# Global flag to control the monitoring thread
monitoring_active = True

# Track connected clients for auto-shutdown
connected_clients = 0

def start_system_monitor():
    """Start the system monitoring background thread."""
    def emit_system_info():
        global monitoring_active
        while monitoring_active:
            try:
                socketio.sleep(2)  # Update every 2 seconds
                if monitoring_active:  # Check again after sleep
                    socketio.emit('system_info', {
                        'cpu': system_monitor.get_cpu_usage(),
                        'memory': system_monitor.get_memory_usage(),
                        'processes': system_monitor.get_process_count()
                    })
            except Exception as e:
                log(f"Error in system monitor: {str(e)}")
                break

    # Start the background task
    socketio.start_background_task(emit_system_info)

def stop_system_monitor():
    """Stop the system monitoring background thread."""
    global monitoring_active
    monitoring_active = False
    log("System monitoring stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    log(f"Received signal {signum}, shutting down...")
    stop_system_monitor()
    sys.exit(0)

if __name__ == '__main__':
    log("Starting Terminal Project")
    print(f"[TERMINAL] Server will be available at: http://127.0.0.1:{os.environ.get('PORT', '5000')}")

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Ensure required directories exist
    os.makedirs(os.path.join('static', 'temp'), exist_ok=True)

    # Start system monitoring
    start_system_monitor()

    port = int(os.environ.get("PORT", 5000))
    log(f"Starting server on port {port}...")
    log("Server is running. Close this window or use Task Manager to stop.")

    # Use socketio.run() - it should handle shutdown properly
    try:
        socketio.run(app, host='127.0.0.1', port=port)
    except Exception as e:
        log(f"Server error: {str(e)}")
    finally:
        stop_system_monitor()
        log("Server shutdown complete")
