"""
History Manager Module
Manages command history persistence, formatting, and retrieval.
"""

import os
import json
import time
from datetime import datetime
import threading

# Path to the history file
HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'history.json')

# Lock for thread-safe operations
_lock = threading.Lock()

# Initialize global variables
_history_cache = {}
_full_history = []

def _ensure_history_file():
    """Ensure the history file and directory exist."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f:
            json.dump({'tabs': {}, 'full_history': []}, f)

def _load_history():
    """Load history from file."""
    _ensure_history_file()
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
            return data.get('tabs', {}), data.get('full_history', [])
    except (json.JSONDecodeError, FileNotFoundError):
        return {}, []

def _save_history():
    """Save history to file."""
    global _history_cache, _full_history
    _ensure_history_file()
    with _lock:
        try:
            with open(HISTORY_FILE, 'w') as f:
                json.dump({
                    'tabs': _history_cache,
                    'full_history': _full_history
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

def add_command(command, tab_id='default'):
    """
    Add a command to the history.
    
    Args:
        command (str): The command to add
        tab_id (str): The ID of the tab the command was executed in
    """
    global _history_cache, _full_history
    
    with _lock:
        # Load history if cache is empty
        if not _history_cache:
            _history_cache, _full_history = _load_history()
        
        # Initialize tab history if it doesn't exist
        if tab_id not in _history_cache:
            _history_cache[tab_id] = []
        
        # Add command to tab history
        _history_cache[tab_id].append(command)
        
        # Add command to full history with timestamp and tab info
        _full_history.append({
            'command': command,
            'tab_id': tab_id,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'unix_time': time.time()
        })
        
        # Save history to file
        _save_history()

def add_output(command, output, tab_id='default'):
    """
    Add a command and its output to the history.
    
    Args:
        command (str): The command that was executed
        output (str): The output of the command
        tab_id (str): The ID of the tab the command was executed in
    """
    global _history_cache, _full_history
    
    with _lock:
        # Load history if cache is empty
        if not _history_cache:
            _history_cache, _full_history = _load_history()
        
        # Add command to full history with output
        _full_history.append({
            'command': command,
            'output': output,
            'tab_id': tab_id,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'unix_time': time.time()
        })
        
        # Save history to file
        _save_history()

def get_history(tab_id='default'):
    """
    Get the command history for a tab.
    
    Args:
        tab_id (str): The ID of the tab to get history for
        
    Returns:
        list: A list of commands
    """
    global _history_cache, _full_history
    
    with _lock:
        # Load history if cache is empty
        if not _history_cache:
            _history_cache, _full_history = _load_history()
        return _history_cache.get(tab_id, [])

def get_full_history():
    """
    Get the full command history with outputs.
    
    Returns:
        list: A list of dictionaries containing commands, outputs, and metadata
    """
    global _history_cache, _full_history
    
    with _lock:
        # Load history if cache is empty
        if not _full_history:
            _history_cache, _full_history = _load_history()
        return _full_history

def clear_history(tab_id=None):
    """
    Clear the command history.
    
    Args:
        tab_id (str, optional): The ID of the tab to clear history for.
                               If None, clear all history.
    """
    with _lock:
        global _history_cache, _full_history
        
        if tab_id:
            # Clear history for a specific tab
            if tab_id in _history_cache:
                _history_cache[tab_id] = []
                # Filter out entries for this tab from full history
                _full_history = [entry for entry in _full_history if entry.get('tab_id') != tab_id]
        else:
            # Clear all history
            _history_cache = {}
            _full_history = []
        
        # Save history to file
        _save_history()

def format_history_text(history_data):
    """
    Format history data as plain text.
    
    Args:
        history_data (list): The history data to format
        
    Returns:
        str: Formatted history as plain text
    """
    lines = []
    
    for entry in history_data:
        timestamp = entry.get('timestamp', 'Unknown time')
        tab_id = entry.get('tab_id', 'default')
        command = entry.get('command', '')
        output = entry.get('output', '')
        
        lines.append(f"[{timestamp}] [{tab_id}] $ {command}")
        if output:
            # Indent output lines
            output_lines = output.split('\n')
            for line in output_lines:
                lines.append(f"  {line}")
            lines.append("")  # Empty line after output
    
    return '\n'.join(lines)

def format_history_markdown(history_data):
    """
    Format history data as Markdown.
    
    Args:
        history_data (list): The history data to format
        
    Returns:
        str: Formatted history as Markdown
    """
    lines = ["# Terminal Command History", ""]
    
    current_date = None
    
    for entry in history_data:
        timestamp = entry.get('timestamp', 'Unknown time')
        tab_id = entry.get('tab_id', 'default')
        command = entry.get('command', '')
        output = entry.get('output', '')
        
        # Extract date from timestamp
        date = timestamp.split(' ')[0] if ' ' in timestamp else timestamp
        
        # Add date header if it's a new date
        if date != current_date:
            current_date = date
            lines.append(f"## {date}")
            lines.append("")
        
        # Add command with timestamp and tab
        lines.append(f"### {timestamp} (Tab: {tab_id})")
        lines.append("")
        lines.append("```bash")
        lines.append(f"$ {command}")
        lines.append("```")
        lines.append("")
        
        # Add output if available
        if output:
            lines.append("**Output:**")
            lines.append("")
            lines.append("```")
            lines.append(output)
            lines.append("```")
            lines.append("")
    
    return '\n'.join(lines)

def search_history(query, tab_id=None):
    """Search command history for a query."""
    global _history_cache, _full_history
    
    with _lock:
        # Load history if cache is empty
        if not _full_history:
            _history_cache, _full_history = _load_history()
        
        # Convert query to lowercase for case-insensitive search
        query = query.lower()
        
        # Filter history entries
        results = []
        for entry in _full_history:
            if tab_id and entry.get('tab_id') != tab_id:
                continue
            
            command = entry.get('command', '').lower()
            output = entry.get('output', '').lower()
            
            if query in command or query in output:
                results.append(entry)
        
        return results

# Initialize history on module load
_history_cache, _full_history = _load_history()
