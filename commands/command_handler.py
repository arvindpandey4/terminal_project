"""
Command Handler Module
Handles execution of terminal commands and provides autocomplete functionality.
"""

import os
import shutil
import glob
import subprocess
import platform
import re
import psutil
import time
from difflib import get_close_matches

# Dictionary of available commands and their descriptions
AVAILABLE_COMMANDS = {
    'ls': 'List directory contents',
    'dir': 'List directory contents (Windows)',
    'cd': 'Change directory',
    'pwd': 'Print working directory',
    'mkdir': 'Make directory',
    'rmdir': 'Remove directory',
    'rm': 'Remove file or directory',
    'cp': 'Copy file or directory',
    'mv': 'Move file or directory',
    'cat': 'Display file contents',
    'echo': 'Display a line of text',
    'touch': 'Create an empty file',
    'grep': 'Search for patterns in files',
    'find': 'Search for files',
    'ps': 'Report process status',
    'top': 'Display system processes',
    'clear': 'Clear the terminal screen',
    'history': 'Show command history',
    'help': 'Display help information',
    'exit': 'Exit the terminal',
    'cpu': 'Display CPU information',
    'memory': 'Display memory information',
    'processes': 'List running processes'
}

def execute_command(command, current_dir):
    """
    Execute a terminal command and return the output.

    Args:
        command (str): The command to execute
        current_dir (str): The current working directory

    Returns:
        dict: A dictionary containing the command output and optionally a new directory
    """
    # Handle empty command
    if not command or command.strip() == "":
        return {
            'output': '',
            'new_dir': None
        }
    
    # Split the command into parts
    parts = command.split()
    cmd = parts[0].lower() if parts else ""
    args = parts[1:] if len(parts) > 1 else []

    result = {
        'output': '',
        'new_dir': None
    }

    try:
        # Handle built-in commands
        if cmd == 'ls' or (cmd == 'dir' and platform.system() == 'Windows'):
            result['output'] = handle_ls(args, current_dir)

        elif cmd == 'cd':
            new_dir = handle_cd(args, current_dir)
            result['output'] = f"Changed directory to: {new_dir}"
            result['new_dir'] = new_dir

        elif cmd == 'pwd':
            result['output'] = handle_pwd(current_dir)

        elif cmd == 'mkdir':
            result['output'] = handle_mkdir(args, current_dir)

        elif cmd == 'rmdir':
            result['output'] = handle_rmdir(args, current_dir)

        elif cmd == 'rm':
            result['output'] = handle_rm(args, current_dir)

        elif cmd == 'cp':
            result['output'] = handle_cp(args, current_dir)

        elif cmd == 'mv':
            result['output'] = handle_mv(args, current_dir)

        elif cmd == 'cat':
            result['output'] = handle_cat(args, current_dir)

        elif cmd == 'echo':
            result['output'] = handle_echo(args)

        elif cmd == 'touch':
            result['output'] = handle_touch(args, current_dir)

        elif cmd == 'grep':
            result['output'] = handle_grep(args, current_dir)

        elif cmd == 'find':
            result['output'] = handle_find(args, current_dir)

        elif cmd == 'ps':
            result['output'] = handle_ps()

        elif cmd == 'top':
            result['output'] = handle_top()

        elif cmd == 'clear':
            result['output'] = handle_clear()

        elif cmd == 'test':
            result['output'] = "Test command working! The output system is functional."

        elif cmd == 'help':
            result['output'] = handle_help(args)

        elif cmd == 'exit':
            result['output'] = handle_exit()

        elif cmd == 'cpu':
            result['output'] = handle_cpu_info()

        elif cmd == 'memory':
            result['output'] = handle_memory_info()

        elif cmd == 'processes':
            result['output'] = handle_process_list()

        else:
            # Try to find similar commands for suggestions
            suggestions = get_close_matches(cmd, AVAILABLE_COMMANDS.keys(), n=3, cutoff=0.6)

            if suggestions:
                suggestion_text = f"Command '{cmd}' not found. Did you mean: {', '.join(suggestions)}?"
                result['output'] = suggestion_text
            else:
                # If no built-in command matches, try to execute as a system command
                try:
                    # Check for potentially dangerous commands
                    dangerous_commands = ['rm -rf /', 'rm -rf /*', 'dd', 'mkfs', 'format']
                    if any(dangerous_cmd in command.lower() for dangerous_cmd in dangerous_commands):
                        result['output'] = f"Error: Potentially dangerous command '{command}' blocked for safety reasons."
                        return result
                    
                    # Use subprocess to execute the command
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=current_dir,
                        universal_newlines=True
                    )
                    stdout, stderr = process.communicate(timeout=10)

                    if stderr:
                        result['output'] = stderr.strip()
                    else:
                        result['output'] = stdout.strip() if stdout.strip() else "(Command executed successfully with no output)"
                except subprocess.TimeoutExpired:
                    result['output'] = "Command timed out after 10 seconds"
                except Exception as e:
                    result['output'] = f"Command '{cmd}' not found or could not be executed: {str(e)}"

    except Exception as e:
        result['output'] = f"Error executing command: {str(e)}"

    # Ensure output is never empty for successful commands
    if not result['output'] and cmd in ['ls', 'pwd', 'help', 'echo']:
        if cmd == 'ls':
            result['output'] = "(empty directory)"
        elif cmd == 'pwd':
            result['output'] = current_dir
        elif cmd == 'help':
            result['output'] = "Type 'help' for available commands"
        elif cmd == 'echo':
            result['output'] = ""

    return result

def handle_ls(args, current_dir):
    """Handle ls command."""
    try:
        path = current_dir
        show_hidden = False
        long_format = False
        
        # Parse arguments
        for arg in args:
            if arg.startswith('-'):
                if 'a' in arg:
                    show_hidden = True
                if 'l' in arg:
                    long_format = True
            else:
                if os.path.isabs(arg):
                    path = arg
                else:
                    path = os.path.join(current_dir, arg)

        # Check if path exists
        if not os.path.exists(path):
            return f"ls: cannot access '{args[-1] if args and not args[-1].startswith('-') else path}': No such file or directory"

        # Get list of files and directories
        items = os.listdir(path)
        
        # Filter hidden files if not showing them
        if not show_hidden:
            items = [item for item in items if not item.startswith('.')]

        if not items:
            return "(empty directory)"

        # Format output
        if long_format:
            output = []
            for item in sorted(items):
                item_path = os.path.join(path, item)
                try:
                    stat_info = os.stat(item_path)
                    # Format: permissions, size, modified date, name
                    perms = "d" if os.path.isdir(item_path) else "-"
                    perms += "rwxrwxrwx" if os.access(item_path, os.R_OK | os.W_OK | os.X_OK) else "---------"
                    size = stat_info.st_size
                    mod_time = time.strftime("%b %d %H:%M", time.localtime(stat_info.st_mtime))
                    name = f"{item}/" if os.path.isdir(item_path) else item
                    output.append(f"{perms} {size:8d} {mod_time} {name}")
                except Exception:
                    output.append(f"??????????? ???????? {item}")
            return "\n".join(output)
        else:
            output = []
            for item in sorted(items):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    output.append(f"{item}/")  # Directory indicator
                else:
                    output.append(item)
            return "  ".join(output)
    except PermissionError:
        return f"ls: cannot open directory '{path}': Permission denied"
    except Exception as e:
        return f"ls: error: {str(e)}"

def handle_pwd(current_dir):
    """Handle pwd command."""
    return current_dir

def handle_echo(args):
    """Handle echo command."""
    return ' '.join(args)

def handle_clear():
    """Handle clear command."""
    return '\n' * 50  # Simulate clearing the screen

def handle_exit():
    """Handle exit command."""
    return "Exiting terminal..."

def handle_cd(args, current_dir):
    """Handle cd command."""
    if not args:
        # cd without args goes to home directory
        return os.path.expanduser("~")
    
    path = args[0]
    
    # Handle special paths
    if path == "..":
        return os.path.dirname(current_dir)
    elif path == ".":
        return current_dir
    elif path == "~":
        return os.path.expanduser("~")
    
    # Handle absolute and relative paths
    if os.path.isabs(path):
        new_dir = path
    else:
        new_dir = os.path.join(current_dir, path)
    
    # Normalize path
    new_dir = os.path.normpath(new_dir)
    
    # Check if directory exists
    if not os.path.exists(new_dir):
        raise FileNotFoundError(f"cd: {path}: No such file or directory")
    
    if not os.path.isdir(new_dir):
        raise NotADirectoryError(f"cd: {path}: Not a directory")
    
    return new_dir

def handle_mkdir(args, current_dir):
    """Handle mkdir command."""
    if not args:
        return "mkdir: missing operand"
    
    # Check for -p flag
    create_parents = '-p' in args
    
    # Filter out options
    paths = [arg for arg in args if not arg.startswith('-')]
    
    if not paths:
        return "mkdir: missing operand"
    
    results = []
    for path in paths:
        # Handle absolute and relative paths
        if os.path.isabs(path):
            new_dir = path
        else:
            new_dir = os.path.join(current_dir, path)
        
        # Create directory
        try:
            os.makedirs(new_dir, exist_ok=create_parents)
            results.append(f"Directory created: {new_dir}")
        except FileExistsError:
            results.append(f"mkdir: cannot create directory '{path}': File exists")
        except PermissionError:
            results.append(f"mkdir: cannot create directory '{path}': Permission denied")
        except Exception as e:
            results.append(f"mkdir: error creating '{path}': {str(e)}")
    
    return "\n".join(results)

def handle_rmdir(args, current_dir):
    """Handle rmdir command."""
    if not args:
        return "rmdir: missing operand"
    
    path = args[0]
    
    # Handle absolute and relative paths
    if os.path.isabs(path):
        dir_path = path
    else:
        dir_path = os.path.join(current_dir, path)
    
    # Remove directory
    try:
        os.rmdir(dir_path)
        return f"Directory removed: {dir_path}"
    except FileNotFoundError:
        return f"rmdir: failed to remove '{path}': No such file or directory"
    except OSError:
        return f"rmdir: failed to remove '{path}': Directory not empty"
    except Exception as e:
        return f"rmdir: error: {str(e)}"

def handle_rm(args, current_dir):
    """Handle rm command."""
    if not args:
        return "rm: missing operand"
    
    recursive = '-r' in args or '-rf' in args
    force = '-f' in args or '-rf' in args
    
    # Filter out options
    paths = [arg for arg in args if not arg.startswith('-')]
    
    if not paths:
        return "rm: missing operand"
    
    results = []
    for path in paths:
        # Handle absolute and relative paths
        if os.path.isabs(path):
            full_path = path
        else:
            full_path = os.path.join(current_dir, path)
        
        try:
            if os.path.isdir(full_path):
                if recursive:
                    shutil.rmtree(full_path)
                    results.append(f"Removed directory: {full_path}")
                else:
                    results.append(f"rm: cannot remove '{path}': Is a directory")
            else:
                os.remove(full_path)
                results.append(f"Removed file: {full_path}")
        except FileNotFoundError:
            if not force:
                results.append(f"rm: cannot remove '{path}': No such file or directory")
        except Exception as e:
            results.append(f"rm: error removing '{path}': {str(e)}")
    
    return "\n".join(results)

def handle_cp(args, current_dir):
    """Handle cp command."""
    if len(args) < 2:
        return "cp: missing file operand"
    
    recursive = '-r' in args or '-R' in args
    
    # Filter out options
    paths = [arg for arg in args if not arg.startswith('-')]
    
    if len(paths) < 2:
        return "cp: missing destination file operand after '{}'".format(paths[0])
    
    source = paths[0]
    destination = paths[1]
    
    # Handle absolute and relative paths
    if os.path.isabs(source):
        source_path = source
    else:
        source_path = os.path.join(current_dir, source)
    
    if os.path.isabs(destination):
        dest_path = destination
    else:
        dest_path = os.path.join(current_dir, destination)
    
    try:
        if os.path.isdir(source_path):
            if recursive:
                if os.path.exists(dest_path) and not os.path.isdir(dest_path):
                    return f"cp: cannot overwrite non-directory '{destination}' with directory '{source}'"
                
                # Create destination directory if it doesn't exist
                os.makedirs(dest_path, exist_ok=True)
                
                # Copy directory recursively
                for item in os.listdir(source_path):
                    s = os.path.join(source_path, item)
                    d = os.path.join(dest_path, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                
                return f"Copied directory: {source_path} -> {dest_path}"
            else:
                return f"cp: -r not specified; omitting directory '{source}'"
        else:
            if os.path.isdir(dest_path):
                dest_path = os.path.join(dest_path, os.path.basename(source_path))
            
            shutil.copy2(source_path, dest_path)
            return f"Copied file: {source_path} -> {dest_path}"
    except FileNotFoundError:
        return f"cp: cannot stat '{source}': No such file or directory"
    except Exception as e:
        return f"cp: error: {str(e)}"

def handle_mv(args, current_dir):
    """Handle mv command."""
    if len(args) < 2:
        return "mv: missing file operand"
    
    # Filter out options
    paths = [arg for arg in args if not arg.startswith('-')]
    
    if len(paths) < 2:
        return "mv: missing destination file operand after '{}'".format(paths[0])
    
    source = paths[0]
    destination = paths[1]
    
    # Handle absolute and relative paths
    if os.path.isabs(source):
        source_path = source
    else:
        source_path = os.path.join(current_dir, source)
    
    if os.path.isabs(destination):
        dest_path = destination
    else:
        dest_path = os.path.join(current_dir, destination)
    
    try:
        if os.path.isdir(dest_path) and not os.path.isdir(source_path):
            # If destination is a directory, move the file into it
            dest_path = os.path.join(dest_path, os.path.basename(source_path))
        
        # Move file or directory
        shutil.move(source_path, dest_path)
        return f"Moved: {source_path} -> {dest_path}"
    except FileNotFoundError:
        return f"mv: cannot stat '{source}': No such file or directory"
    except Exception as e:
        return f"mv: error: {str(e)}"

def handle_cat(args, current_dir):
    """Handle cat command."""
    if not args:
        return "cat: missing operand"
    
    results = []
    for path in args:
        # Handle absolute and relative paths
        if os.path.isabs(path):
            file_path = path
        else:
            file_path = os.path.join(current_dir, path)
        
        try:
            if os.path.isdir(file_path):
                results.append(f"cat: {path}: Is a directory")
                continue
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            results.append(content)
        except FileNotFoundError:
            results.append(f"cat: {path}: No such file or directory")
        except Exception as e:
            results.append(f"cat: {path}: {str(e)}")
    
    return "\n".join(results)

def handle_touch(args, current_dir):
    """Handle touch command."""
    if not args:
        return "touch: missing file operand"
    
    results = []
    for path in args:
        # Handle absolute and relative paths
        if os.path.isabs(path):
            file_path = path
        else:
            file_path = os.path.join(current_dir, path)
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
            
            # Create or update file
            with open(file_path, 'a'):
                os.utime(file_path, None)  # Update timestamp
            
            results.append(f"Touched file: {file_path}")
        except Exception as e:
            results.append(f"touch: cannot touch '{path}': {str(e)}")
    
    return "\n".join(results)

def handle_grep(args, current_dir):
    """Handle grep command."""
    if len(args) < 2:
        return "grep: missing pattern or file operand"
    
    pattern = args[0]
    files = args[1:]
    
    results = []
    for file_pattern in files:
        # Handle absolute and relative paths
        if os.path.isabs(file_pattern):
            path_pattern = file_pattern
        else:
            path_pattern = os.path.join(current_dir, file_pattern)
        
        # Expand wildcards
        file_paths = glob.glob(path_pattern)
        
        if not file_paths:
            results.append(f"grep: {file_pattern}: No such file or directory")
            continue
        
        for file_path in file_paths:
            if os.path.isdir(file_path):
                results.append(f"grep: {file_path}: Is a directory")
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    for i, line in enumerate(f, 1):
                        if re.search(pattern, line):
                            # Format: filename:line_number:content
                            results.append(f"{file_path}:{i}:{line.rstrip()}")
            except Exception as e:
                results.append(f"grep: {file_path}: {str(e)}")
    
    return "\n".join(results)

def handle_find(args, current_dir):
    """Handle find command."""
    if not args:
        return "find: missing path operand"
    
    # Parse arguments
    path = args[0]
    name_pattern = None
    
    for i, arg in enumerate(args):
        if arg == "-name" and i + 1 < len(args):
            name_pattern = args[i + 1]
            break
    
    # Handle absolute and relative paths
    if os.path.isabs(path):
        search_path = path
    else:
        search_path = os.path.join(current_dir, path)
    
    if not os.path.exists(search_path):
        return f"find: '{path}': No such file or directory"
    
    results = []
    
    try:
        for root, dirs, files in os.walk(search_path):
            # Add directories
            for d in dirs:
                full_path = os.path.join(root, d)
                rel_path = os.path.relpath(full_path, current_dir)
                
                if name_pattern is None or glob.fnmatch.fnmatch(d, name_pattern):
                    results.append(rel_path)
            
            # Add files
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, current_dir)
                
                if name_pattern is None or glob.fnmatch.fnmatch(f, name_pattern):
                    results.append(rel_path)
    except Exception as e:
        return f"find: error: {str(e)}"
    
    return "\n".join(results)

def handle_ps():
    """Handle ps command."""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                processes.append(f"{pinfo['pid']}\t{pinfo['cpu_percent']:.1f}\t{pinfo['memory_percent']:.1f}\t{pinfo['username'] or 'N/A'}\t{pinfo['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        if not processes:
            return "No processes found"

        header = "PID\tCPU%\tMEM%\tUSER\tCOMMAND"
        return header + "\n" + "\n".join(processes[:20])  # Limit to 20 processes
    except Exception as e:
        return f"ps: error: {str(e)}"

def handle_top():
    """Handle top command."""
    try:
        # Get system information
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        # Get process information
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                processes.append((
                    pinfo['pid'],
                    pinfo['cpu_percent'] or 0,
                    pinfo['memory_percent'] or 0,
                    pinfo['username'] or 'N/A',
                    pinfo['name'] or 'unknown'
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Sort processes by CPU usage
        processes.sort(key=lambda x: x[1], reverse=True)

        # Format output
        output = [
            f"CPU Usage: {cpu_percent:.1f}%",
            f"Memory: {memory.percent:.1f}% used ({memory.used // (1024*1024)} MB / {memory.total // (1024*1024)} MB)",
            "",
            "PID\tCPU%\tMEM%\tUSER\tCOMMAND"
        ]

        # Add top 10 processes
        for pid, cpu, mem, user, name in processes[:10]:
            output.append(f"{pid}\t{cpu:.1f}\t{mem:.1f}\t{user}\t{name}")

        return "\n".join(output)
    except Exception as e:
        return f"top: error: {str(e)}"

def handle_help(args):
    """Handle help command."""
    if not args:
        # General help
        help_text = ["Available commands:"]
        
        for cmd, desc in sorted(AVAILABLE_COMMANDS.items()):
            help_text.append(f"  {cmd.ljust(10)} - {desc}")
        
        return "\n".join(help_text)
    else:
        # Help for specific command
        cmd = args[0].lower()
        if cmd in AVAILABLE_COMMANDS:
            return f"{cmd} - {AVAILABLE_COMMANDS[cmd]}"
        else:
            return f"help: no help topics match '{cmd}'"

def handle_cpu_info():
    """Handle cpu command."""
    try:
        cpu_info = {
            'physical_cores': psutil.cpu_count(logical=False),
            'total_cores': psutil.cpu_count(logical=True),
            'cpu_percent': psutil.cpu_percent(interval=0.1, percpu=True),
            'cpu_freq': psutil.cpu_freq(),
        }

        output = [
            f"Physical cores: {cpu_info['physical_cores'] or 'N/A'}",
            f"Total cores: {cpu_info['total_cores'] or 'N/A'}",
        ]

        if cpu_info['cpu_freq']:
            output.append(f"Current frequency: {cpu_info['cpu_freq'].current:.1f} MHz")

        output.append("CPU Usage Per Core:")

        if cpu_info['cpu_percent']:
            for i, percent in enumerate(cpu_info['cpu_percent']):
                output.append(f"  Core {i}: {percent:.1f}%")

            avg_usage = sum(cpu_info['cpu_percent']) / len(cpu_info['cpu_percent'])
            output.append(f"Total CPU Usage: {avg_usage:.1f}%")
        else:
            output.append("  Unable to get CPU usage information")

        return "\n".join(output)
    except Exception as e:
        return f"cpu: error: {str(e)}"

def handle_memory_info():
    """Handle memory command."""
    try:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        output = [
            "Memory Information:",
            f"  Total: {memory.total // (1024*1024)} MB",
            f"  Available: {memory.available // (1024*1024)} MB",
            f"  Used: {memory.used // (1024*1024)} MB ({memory.percent:.1f}%)",
            f"  Free: {memory.free // (1024*1024)} MB",
        ]

        if swap.total > 0:
            output.extend([
                "",
                "Swap Information:",
                f"  Total: {swap.total // (1024*1024)} MB",
                f"  Used: {swap.used // (1024*1024)} MB ({swap.percent:.1f}%)",
                f"  Free: {swap.free // (1024*1024)} MB"
            ])

        return "\n".join(output)
    except Exception as e:
        return f"memory: error: {str(e)}"

def handle_process_list():
    """Handle processes command."""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'status']):
            try:
                pinfo = proc.info
                processes.append(f"{pinfo['pid']}\t{pinfo['status']}\t{pinfo['username'] or 'N/A'}\t{pinfo['name'] or 'unknown'}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        if not processes:
            return "No processes found"

        header = "PID\tSTATUS\tUSER\tCOMMAND"
        return header + "\n" + "\n".join(processes[:20])  # Limit to 20 processes
    except Exception as e:
        return f"processes: error: {str(e)}"

def get_autocomplete_suggestions(partial_command, current_dir):
    """
    Get autocomplete suggestions for a partial command.
    
    Args:
        partial_command (str): The partial command to autocomplete
        current_dir (str): The current working directory
        
    Returns:
        list: A list of autocomplete suggestions
    """
    suggestions = []
    
    # Handle empty input
    if not partial_command or partial_command.strip() == "":
        # Return all available commands
        return sorted(AVAILABLE_COMMANDS.keys())
    
    # Split the command into parts
    parts = partial_command.split()
    
    if not parts:
        # Return all available commands
        return sorted(AVAILABLE_COMMANDS.keys())
    
    if len(parts) == 1:
        # Autocomplete command name
        cmd_prefix = parts[0].lower()
        for cmd in AVAILABLE_COMMANDS:
            if cmd.startswith(cmd_prefix):
                suggestions.append(cmd)
        
        # If no command matches, suggest similar commands
        if not suggestions:
            similar_cmds = get_close_matches(cmd_prefix, AVAILABLE_COMMANDS.keys(), n=5, cutoff=0.5)
            suggestions.extend(similar_cmds)
    else:
        # Autocomplete command arguments (files and directories)
        cmd = parts[0].lower()
        last_part = parts[-1]
        
        # Commands that accept file/directory arguments
        file_commands = ['ls', 'cd', 'cat', 'rm', 'cp', 'mv', 'mkdir', 'rmdir', 'touch', 'grep', 'find']
        
        # Commands that accept command flags
        flag_commands = {
            'ls': ['-a', '-l', '-la', '-al'],
            'rm': ['-r', '-f', '-rf'],
            'cp': ['-r', '-R'],
            'grep': ['-i', '-r', '-v', '-n'],
            'find': ['-name', '-type', '-size']
        }
        
        # Suggest flags if the last part starts with a dash
        if cmd in flag_commands and last_part.startswith('-'):
            for flag in flag_commands[cmd]:
                if flag.startswith(last_part):
                    suggestions.append(flag)
        
        # Suggest files and directories
        elif cmd in file_commands and not last_part.startswith('-'):
            # Handle absolute and relative paths
            if os.path.isabs(last_part):
                base_dir = os.path.dirname(last_part) or '/'
                prefix = os.path.basename(last_part)
            else:
                if os.path.dirname(last_part):
                    base_dir = os.path.join(current_dir, os.path.dirname(last_part))
                    prefix = os.path.basename(last_part)
                else:
                    base_dir = current_dir
                    prefix = last_part
            
            # Get matching files and directories
            try:
                for item in os.listdir(base_dir):
                    if item.startswith(prefix):
                        full_path = os.path.join(base_dir, item)
                        if os.path.isdir(full_path):
                            # Add trailing slash for directories
                            suggestions.append(os.path.join(os.path.dirname(last_part), item) + '/')
                        else:
                            suggestions.append(os.path.join(os.path.dirname(last_part), item))
            except (FileNotFoundError, PermissionError, NotADirectoryError):
                # Handle various directory access errors silently
                pass
            except Exception:
                # Catch any other errors silently
                pass
    
    return sorted(suggestions)
