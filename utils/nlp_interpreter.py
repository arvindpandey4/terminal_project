"""
NLP Interpreter Module
Converts natural language commands into terminal commands.
"""

import re
import os
import shlex
from difflib import get_close_matches

# Dictionary of command patterns and their corresponding terminal commands
COMMAND_PATTERNS = [
    # File operations
    {
        'patterns': [
            r'create (?:a )?(?:new )?(?:empty )?file (?:called |named )?(?P<filename>\S+)',
            r'make (?:a )?(?:new )?(?:empty )?file (?:called |named )?(?P<filename>\S+)'
        ],
        'command': 'touch {filename}'
    },
    {
        'patterns': [
            r'create (?:a )?(?:new )?directory (?:called |named )?(?P<dirname>\S+)',
            r'make (?:a )?(?:new )?directory (?:called |named )?(?P<dirname>\S+)',
            r'create (?:a )?(?:new )?folder (?:called |named )?(?P<dirname>\S+)',
            r'make (?:a )?(?:new )?folder (?:called |named )?(?P<dirname>\S+)'
        ],
        'command': 'mkdir {dirname}'
    },
    {
        'patterns': [
            r'(?:show|display|list) (?:the )?(?:files|contents) (?:in|of)(?: the)? (?:directory|folder)?(?: (?P<dirname>\S+))?',
            r'(?:show|display|list) (?:the )?(?:directory|folder)(?: (?P<dirname>\S+))?',
            r'what(?:\'s| is) in(?: the)? (?:directory|folder)(?: (?P<dirname>\S+))?'
        ],
        'command': 'ls {dirname}'
    },
    {
        'patterns': [
            r'(?:show|display|print) (?:the )?contents of(?: the)? file (?P<filename>\S+)',
            r'(?:show|display|print) (?:the )?file (?P<filename>\S+)',
            r'read (?:the )?file (?P<filename>\S+)',
            r'what(?:\'s| is) in(?: the)? file (?P<filename>\S+)'
        ],
        'command': 'cat {filename}'
    },
    {
        'patterns': [
            r'(?:remove|delete) (?:the )?file (?P<filename>\S+)',
            r'(?:remove|delete) (?P<filename>\S+)'
        ],
        'command': 'rm {filename}'
    },
    {
        'patterns': [
            r'(?:remove|delete) (?:the )?(?:directory|folder) (?P<dirname>\S+)',
            r'(?:remove|delete) (?:the )?(?:directory|folder) (?P<dirname>\S+) and (?:its|all its) contents',
            r'(?:remove|delete) (?:the )?(?:directory|folder) (?P<dirname>\S+) recursively'
        ],
        'command': 'rm -r {dirname}'
    },
    {
        'patterns': [
            r'copy (?:the )?file (?P<source>\S+) to (?P<destination>\S+)',
            r'copy (?P<source>\S+) to (?P<destination>\S+)'
        ],
        'command': 'cp {source} {destination}'
    },
    {
        'patterns': [
            r'copy (?:the )?(?:directory|folder) (?P<source>\S+) to (?P<destination>\S+)',
            r'copy (?:the )?(?:directory|folder) (?P<source>\S+) and (?:its|all its) contents to (?P<destination>\S+)'
        ],
        'command': 'cp -r {source} {destination}'
    },
    {
        'patterns': [
            r'move (?:the )?file (?P<source>\S+) to (?P<destination>\S+)',
            r'move (?P<source>\S+) to (?P<destination>\S+)'
        ],
        'command': 'mv {source} {destination}'
    },
    {
        'patterns': [
            r'rename (?:the )?file (?P<source>\S+) to (?P<destination>\S+)',
            r'rename (?P<source>\S+) to (?P<destination>\S+)'
        ],
        'command': 'mv {source} {destination}'
    },
    
    # Navigation
    {
        'patterns': [
            r'(?:change|switch) (?:to )?(?:the )?(?:directory|folder) (?P<dirname>\S+)',
            r'(?:change|switch) (?:to )?(?:the )?(?:directory|folder) (?P<dirname>.+)',
            r'go to (?:the )?(?:directory|folder) (?P<dirname>\S+)',
            r'go to (?:the )?(?:directory|folder) (?P<dirname>.+)',
            r'cd (?:to )?(?P<dirname>\S+)',
            r'cd (?:to )?(?P<dirname>.+)'
        ],
        'command': 'cd {dirname}'
    },
    {
        'patterns': [
            r'(?:show|display|print) (?:the )?current (?:directory|folder|path)',
            r'where am i',
            r'what (?:directory|folder|path) am i in',
            r'what(?:\'s| is) (?:the )?current (?:directory|folder|path)'
        ],
        'command': 'pwd'
    },
    {
        'patterns': [
            r'go (?:back|up)(?: one level)?',
            r'go to (?:the )?parent (?:directory|folder)'
        ],
        'command': 'cd ..'
    },
    {
        'patterns': [
            r'go (?:to )?home',
            r'go to (?:the )?home (?:directory|folder)'
        ],
        'command': 'cd ~'
    },
    
    # Search
    {
        'patterns': [
            r'find (?:all )?files (?:named|called) (?P<filename>\S+)',
            r'search for (?:all )?files (?:named|called) (?P<filename>\S+)',
            r'locate (?:all )?files (?:named|called) (?P<filename>\S+)'
        ],
        'command': 'find . -name {filename}'
    },
    {
        'patterns': [
            r'find (?:all )?files containing (?:the )?(?:text|string|pattern) (?P<pattern>\S+)',
            r'search for (?:all )?files containing (?:the )?(?:text|string|pattern) (?P<pattern>\S+)',
            r'grep (?:for )?(?P<pattern>\S+)'
        ],
        'command': 'grep -r {pattern} .'
    },
    
    # System information
    {
        'patterns': [
            r'(?:show|display) (?:the )?(?:system )?(?:cpu|processor) (?:information|info|usage|stats)',
            r'how (?:is|\'s) (?:the )?(?:cpu|processor) (?:doing)?',
            r'what(?:\'s| is) (?:the )?(?:cpu|processor) (?:usage|load)'
        ],
        'command': 'cpu'
    },
    {
        'patterns': [
            r'(?:show|display) (?:the )?(?:system )?memory (?:information|info|usage|stats)',
            r'how (?:is|\'s) (?:the )?memory (?:doing)?',
            r'what(?:\'s| is) (?:the )?memory (?:usage|load)'
        ],
        'command': 'memory'
    },
    {
        'patterns': [
            r'(?:show|display|list) (?:the )?(?:running )?processes',
            r'what processes are running',
            r'what(?:\'s| is) running'
        ],
        'command': 'processes'
    },
    {
        'patterns': [
            r'(?:show|display) (?:the )?(?:system )?(?:information|info)',
            r'(?:show|display) (?:the )?top (?:processes|process list)',
            r'what(?:\'s| is) (?:the )?(?:system )?(?:doing|status)'
        ],
        'command': 'top'
    },
    
    # Complex operations
    {
        'patterns': [
            r'create (?:a )?folder (?:called |named )?(?P<dirname>\S+) and move all (?P<filetype>\S+) files (?:in|into) it',
            r'move all (?P<filetype>\S+) files (?:in)?to (?:a )?(?:new )?folder (?:called |named )?(?P<dirname>\S+)'
        ],
        'command_generator': lambda matches: [
            f"mkdir {matches['dirname']}",
            f"find . -maxdepth 1 -name \"*.{matches['filetype']}\" -exec mv {{}} {matches['dirname']}/ \\;"
        ]
    },
    {
        'patterns': [
            r'find and delete all (?P<filetype>\S+) files',
            r'delete all (?P<filetype>\S+) files'
        ],
        'command_generator': lambda matches: [
            f"find . -name \"*.{matches['filetype']}\" -delete"
        ]
    },
    {
        'patterns': [
            r'count (?:the )?(?:number of )?files in (?:the )?(?:directory|folder)(?: (?P<dirname>\S+))?'
        ],
        'command_generator': lambda matches: [
            f"ls -1 {matches.get('dirname', '.')} | wc -l"
        ]
    },
    {
        'patterns': [
            r'create (?:a )?backup of (?:the )?file (?P<filename>\S+)'
        ],
        'command_generator': lambda matches: [
            f"cp {matches['filename']} {matches['filename']}.bak"
        ]
    },
    {
        'patterns': [
            r'compress (?:the )?(?:directory|folder) (?P<dirname>\S+)'
        ],
        'command_generator': lambda matches: [
            f"tar -czvf {matches['dirname']}.tar.gz {matches['dirname']}"
        ]
    }
]

def interpret(nl_command):
    """
    Interpret a natural language command and convert it to terminal commands.
    
    Args:
        nl_command (str): The natural language command to interpret
        
    Returns:
        list: A list of terminal commands
    """
    # Clean up the command
    nl_command = nl_command.strip().lower()
    
    # Try to match the command against known patterns
    for pattern_dict in COMMAND_PATTERNS:
        for pattern in pattern_dict['patterns']:
            match = re.match(pattern, nl_command)
            if match:
                # Extract matched groups
                matches = match.groupdict()
                
                # Handle command generation
                if 'command_generator' in pattern_dict:
                    # Use the command generator function
                    return pattern_dict['command_generator'](matches)
                else:
                    # Format the command template with the matched groups
                    command = pattern_dict['command']
                    for key, value in matches.items():
                        if value:
                            # Handle paths with spaces
                            if ' ' in value and not (value.startswith('"') or value.startswith("'")):
                                value = f'"{value}"'
                            command = command.replace(f'{{{key}}}', value)
                        else:
                            # Handle optional parameters
                            command = command.replace(f' {{{key}}}', '')
                    
                    return [command]
    
    # If no pattern matches, try to handle as a direct command
    if nl_command.startswith('run ') or nl_command.startswith('execute '):
        direct_command = nl_command.split(' ', 1)[1]
        return [direct_command]
    
    # If all else fails, return the original command as is
    # This allows users to type actual commands and have them passed through
    return [nl_command]

def suggest_command(partial_command):
    """
    Suggest natural language commands based on a partial input.
    
    Args:
        partial_command (str): The partial command to get suggestions for
        
    Returns:
        list: A list of suggested natural language commands
    """
    suggestions = []
    
    # Create a list of example commands from the patterns
    example_commands = []
    for pattern_dict in COMMAND_PATTERNS:
        for pattern in pattern_dict['patterns']:
            # Convert regex pattern to an example command
            example = pattern
            
            # Replace common regex patterns with examples
            example = re.sub(r'\(\?:.*?\)', '', example)  # Remove non-capturing groups
            example = re.sub(r'\(\?P<(\w+)>\\S\+\)', r'example_\1', example)  # Replace named capture groups
            example = re.sub(r'\(\?P<(\w+)>.+\)', r'example_\1', example)  # Replace named capture groups with .+
            example = re.sub(r'\\S\+', 'example', example)  # Replace \S+
            example = re.sub(r'\?', '', example)  # Remove optional markers
            example = re.sub(r'\|', '', example)  # Remove alternation
            example = re.sub(r'[\[\]\(\)\{\}\.\+\*\^\$]', '', example)  # Remove other regex special chars
            
            # Clean up the example
            example = re.sub(r'\s+', ' ', example).strip()
            if example:
                example_commands.append(example)
    
    # Find close matches
    if partial_command:
        suggestions = get_close_matches(partial_command, example_commands, n=5, cutoff=0.3)
    else:
        # If no partial command, return some common examples
        suggestions = [
            "list files",
            "create file example.txt",
            "show cpu usage",
            "find files named example.txt",
            "move file.txt to folder/"
        ]
    
    return suggestions

def get_help_examples():
    """
    Get a list of example natural language commands.
    
    Returns:
        list: A list of example commands and their descriptions
    """
    examples = [
        ("create file example.txt", "Creates a new empty file"),
        ("create folder documents", "Creates a new directory"),
        ("list files", "Shows files in the current directory"),
        ("show file example.txt", "Displays the contents of a file"),
        ("delete file example.txt", "Removes a file"),
        ("copy file.txt to backup.txt", "Copies a file"),
        ("move file.txt to documents/", "Moves a file to a directory"),
        ("rename file.txt to newname.txt", "Renames a file"),
        ("change directory documents", "Changes to a different directory"),
        ("show current directory", "Shows the current path"),
        ("go back", "Goes up one directory level"),
        ("find files named *.txt", "Searches for files by name"),
        ("find files containing hello", "Searches for text in files"),
        ("show cpu information", "Displays CPU usage and information"),
        ("show memory usage", "Displays memory usage statistics"),
        ("list processes", "Shows running processes"),
        ("create folder logs and move all txt files into it", "Creates a folder and moves files into it"),
        ("count files in directory", "Counts the number of files in a directory"),
        ("create backup of file important.txt", "Creates a backup copy of a file")
    ]
    
    return examples
