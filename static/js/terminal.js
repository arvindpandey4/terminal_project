/**
 * Terminal Project - Frontend JavaScript
 * Handles terminal UI, WebSocket communication, and user interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Socket.IO connection - force polling to avoid WebSocket issues
    const socket = io('/', {
        transports: ['polling'],
        upgrade: false,
        timeout: 20000,
        forceNew: true
    });
    
    // Terminal state
    const state = {
        currentTab: 'default',
        tabs: {
            default: {
                history: [],
                historyIndex: -1,
                currentDirectory: '',
                inputHistory: []
            }
        },
        theme: 'dark',
        systemInfo: {
            cpu: 0,
            memory: 0,
            processes: 0
        }
    };
    
    // DOM Elements
    const elements = {
        terminalTabs: document.getElementById('terminal-tabs'),
        newTabBtn: document.getElementById('new-tab-btn'),
        terminalContent: document.getElementById('terminal-content'),
        themeToggle: document.getElementById('theme-toggle'),
        themeSelector: document.getElementById('theme-selector'),
        exportLogs: document.getElementById('export-logs'),
        quickCommands: document.querySelectorAll('.quick-command'),
        cpuGauge: document.getElementById('cpu-gauge'),
        cpuText: document.getElementById('cpu-text'),
        memoryGauge: document.getElementById('memory-gauge'),
        memoryText: document.getElementById('memory-text'),
        processCount: document.getElementById('process-count')
    };
    
    // Initialize terminal
    function initTerminal() {
        // Set up event listeners
        setupEventListeners();
        
        // Set up socket event handlers
        setupSocketHandlers();
        
        // Focus on the input of the current tab
        focusInput(state.currentTab);
        
        // Display welcome message
        appendOutput(state.currentTab, getWelcomeMessage());
    }
    
    // Set up event listeners
    function setupEventListeners() {
        // New tab button
        elements.newTabBtn.addEventListener('click', createNewTab);
        
        // Tab switching
        elements.terminalTabs.addEventListener('click', (e) => {
            if (e.target.classList.contains('tab')) {
                switchTab(e.target.dataset.tabId);
            }
        });
        
        // Theme toggle
        elements.themeToggle.addEventListener('click', () => {
            const newTheme = document.body.classList.contains('theme-dark') ? 'light' : 'dark';
            setTheme(newTheme);
        });
        
        // Theme selector
        elements.themeSelector.addEventListener('click', (e) => {
            if (e.target.dataset.theme) {
                setTheme(e.target.dataset.theme);
            }
        });
        
        // Export logs
        elements.exportLogs.addEventListener('click', exportLogs);
        
        // Quick commands
        elements.quickCommands.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const command = e.target.dataset.command;
                if (command) {
                    executeCommand(state.currentTab, command);
                }
            });
        });
        
    // Handle terminal input for each tab
    document.addEventListener('keydown', handleTerminalInput);

    // Auto-focus the input when clicking anywhere in the terminal area
    document.addEventListener('click', (e) => {
        // If clicking in a terminal container but not on buttons/links, focus the input
        if (e.target.closest('.terminal-container') && !e.target.closest('button') && !e.target.closest('a')) {
            const terminalContainer = e.target.closest('.terminal-container');
            const input = terminalContainer.querySelector('.terminal-input');
            if (input) {
                input.focus();
            }
        }
    });
    }
    
    // Set up socket event handlers
    function setupSocketHandlers() {
        // Connection established
        socket.on('connect', () => {
            // Connection established silently
        });

        // Receive command output
        socket.on('output', (data) => {
            if (data && data.output) {
                // Use the tab_id from the data, or fall back to current tab
                const tabId = data.tab_id || state.currentTab;
                appendOutput(tabId, data.output);
            }
        });

        // Directory change
        socket.on('directory_change', (data) => {
            if (data.tab_id && data.directory) {
                state.tabs[data.tab_id].currentDirectory = data.directory;
                updatePrompt(data.tab_id);
            }
        });

        // Autocomplete suggestions
        socket.on('autocomplete_suggestions', (data) => {
            if (data.tab_id && data.suggestions) {
                showAutocompleteSuggestions(data.tab_id, data.suggestions);
            }
        });

        // Command history
        socket.on('history', (data) => {
            if (data.tab_id && data.history) {
                state.tabs[data.tab_id].inputHistory = data.history;
            }
        });

        // System information updates
        socket.on('system_info', (data) => {
            updateSystemInfo(data);
        });

        // Handle disconnection
        socket.on('disconnect', () => {
            appendOutput(state.currentTab, 'Connection to server lost. Please refresh the page.', 'error');
        });
    }
    
    // Handle terminal input
    function handleTerminalInput(e) {
        const activeTab = state.currentTab;
        const inputElement = document.querySelector(`#terminal-${activeTab} .terminal-input`);

        // Only process if an input is focused
        if (document.activeElement !== inputElement) {
            return;
        }

        // Handle special keys
        switch (e.key) {
            case 'Enter':
                e.preventDefault();
                const command = inputElement.value.trim();
                if (command) {
                    executeCommand(activeTab, command);
                    inputElement.value = '';
                    state.tabs[activeTab].historyIndex = -1;
                }
                break;

            case 'ArrowUp':
                e.preventDefault();
                navigateHistory(activeTab, 'up');
                break;

            case 'ArrowDown':
                e.preventDefault();
                navigateHistory(activeTab, 'down');
                break;

            case 'Tab':
                e.preventDefault();
                requestAutocomplete(activeTab, inputElement.value);
                break;

            case 'c':
                // Ctrl+C to cancel current command
                if (e.ctrlKey) {
                    e.preventDefault();
                    inputElement.value = '';
                    appendOutput(activeTab, '^C', 'command');
                }
                break;

            case 'l':
                // Ctrl+L to clear screen
                if (e.ctrlKey) {
                    e.preventDefault();
                    clearTerminal(activeTab);
                }
                break;
        }
    }
    
    // Execute a command
    function executeCommand(tabId, command) {
        // Add command to terminal output
        appendOutput(tabId, `$ ${command}`, 'command');

        // Send command to server
        socket.emit('command', {
            command: command,
            tab_id: tabId
        });
    }
    
    // Navigate command history
    function navigateHistory(tabId, direction) {
        const tab = state.tabs[tabId];
        const inputElement = document.querySelector(`#terminal-${tabId} .terminal-input`);
        
        // Request history if we don't have it yet
        if (!tab.inputHistory.length) {
            socket.emit('get_history', { tab_id: tabId });
            return;
        }
        
        if (direction === 'up' && tab.historyIndex < tab.inputHistory.length - 1) {
            tab.historyIndex++;
            inputElement.value = tab.inputHistory[tab.inputHistory.length - 1 - tab.historyIndex];
            // Move cursor to end of input
            setTimeout(() => {
                inputElement.selectionStart = inputElement.selectionEnd = inputElement.value.length;
            }, 0);
        } else if (direction === 'down' && tab.historyIndex > -1) {
            tab.historyIndex--;
            if (tab.historyIndex === -1) {
                inputElement.value = '';
            } else {
                inputElement.value = tab.inputHistory[tab.inputHistory.length - 1 - tab.historyIndex];
            }
        }
    }
    
    // Request autocomplete suggestions
    function requestAutocomplete(tabId, partialCommand) {
        socket.emit('autocomplete', {
            command: partialCommand,
            tab_id: tabId
        });
    }
    
    // Show autocomplete suggestions
    function showAutocompleteSuggestions(tabId, suggestions) {
        if (!suggestions || !suggestions.length) return;
        
        const inputElement = document.querySelector(`#terminal-${tabId} .terminal-input`);
        const currentValue = inputElement.value;
        
        // If there's only one suggestion, use it
        if (suggestions.length === 1) {
            inputElement.value = suggestions[0];
            return;
        }
        
        // Otherwise, show all suggestions
        let output = '\\nSuggestions:\\n';
        suggestions.forEach(suggestion => {
            output += `  ${suggestion}\\n`;
        });
        
        appendOutput(tabId, output);
        
        // Find common prefix among suggestions
        const commonPrefix = findCommonPrefix(suggestions);
        if (commonPrefix.length > currentValue.length) {
            inputElement.value = commonPrefix;
        }
    }
    
    // Find common prefix among strings
    function findCommonPrefix(strings) {
        if (!strings.length) return '';
        if (strings.length === 1) return strings[0];
        
        let prefix = strings[0];
        for (let i = 1; i < strings.length; i++) {
            while (strings[i].indexOf(prefix) !== 0) {
                prefix = prefix.substring(0, prefix.length - 1);
                if (!prefix) return '';
            }
        }
        
        return prefix;
    }
    
    // Append output to terminal
    function appendOutput(tabId, content, type = 'output') {
        const outputElement = document.querySelector(`#terminal-${tabId} .terminal-output`);
        if (!outputElement) {
            return;
        }

        const outputLine = document.createElement('div');
        outputLine.className = `output-line ${type}`;

        // Convert content to string and handle newlines
        if (typeof content !== 'string') {
            content = String(content);
        }

        // Replace newlines with <br> tags for HTML display
        content = content.replace(/\n/g, '<br>');

        // Ensure content is not empty and visible
        if (!content || content.trim() === '') {
            content = '<span style="color: #888;">(no output)</span>';
        }

        outputLine.innerHTML = content;
        outputElement.appendChild(outputLine);

        // Scroll to bottom
        outputElement.scrollTop = outputElement.scrollHeight;
    }

    // Parse ANSI color codes
    function parseAnsiCodes(text) {
        // Replace ANSI color codes with spans
        const ansiColorMap = {
            '\\033[0m': '</span>',
            '\\033[1;30m': '<span style="color: #555;">',
            '\\033[1;31m': '<span style="color: #f55;">',
            '\\033[1;32m': '<span style="color: #5f5;">',
            '\\033[1;33m': '<span style="color: #ff5;">',
            '\\033[1;34m': '<span style="color: #55f;">',
            '\\033[1;35m': '<span style="color: #f5f;">',
            '\\033[1;36m': '<span style="color: #5ff;">',
            '\\033[1;37m': '<span style="color: #fff;">'
        };
        
        // Replace newlines with <br>
        text = text.replace(/\\n/g, '<br>');
        
        // Replace ANSI codes
        for (const [code, replacement] of Object.entries(ansiColorMap)) {
            text = text.replace(new RegExp(code.replace(/\[/g, '\\['), 'g'), replacement);
        }
        
        return text;
    }
    
    // Clear terminal
    function clearTerminal(tabId) {
        const outputElement = document.querySelector(`#terminal-${tabId} .terminal-output`);
        if (outputElement) {
            outputElement.innerHTML = '';
        }
    }
    
    // Update terminal prompt
    function updatePrompt(tabId) {
        const promptElement = document.querySelector(`#terminal-${tabId} .terminal-prompt`);
        if (promptElement) {
            const directory = state.tabs[tabId].currentDirectory || '';
            promptElement.textContent = `${directory} $`;
        }
    }
    
    // Create a new terminal tab
    function createNewTab() {
        const tabCount = Object.keys(state.tabs).length + 1;
        const tabId = `tab${tabCount}`;
        
        // Create tab state
        state.tabs[tabId] = {
            history: [],
            historyIndex: -1,
            currentDirectory: '',
            inputHistory: []
        };
        
        // Create tab button
        const tabButton = document.createElement('div');
        tabButton.className = 'tab px-4 py-2 cursor-pointer';
        tabButton.dataset.tabId = tabId;
        tabButton.textContent = `Terminal ${tabCount}`;
        
        // Insert before the new tab button
        elements.terminalTabs.insertBefore(tabButton, elements.newTabBtn);
        
        // Create terminal container
        const terminalContainer = document.createElement('div');
        terminalContainer.id = `terminal-${tabId}`;
        terminalContainer.className = 'terminal-container h-full flex flex-col hidden';
        
        terminalContainer.innerHTML = `
            <div class="terminal-output flex-1 p-2 overflow-y-auto custom-scrollbar terminal-text"></div>
            <div class="terminal-input-area flex items-center p-2 border-t border-terminal-border theme-transition">
                <span class="terminal-prompt mr-2">$</span>
                <input type="text" class="terminal-input flex-1 bg-transparent border-none outline-none terminal-text" autocomplete="off" spellcheck="false">
            </div>
        `;
        
        elements.terminalContent.appendChild(terminalContainer);
        
        // Switch to the new tab
        switchTab(tabId);
        
        // Display welcome message
        appendOutput(tabId, getWelcomeMessage());
    }
    
    // Switch to a different tab
    function switchTab(tabId) {
        if (!state.tabs[tabId]) return;
        
        // Update active tab
        state.currentTab = tabId;
        
        // Update tab buttons
        document.querySelectorAll('.tab').forEach(tab => {
            if (tab.dataset.tabId === tabId) {
                tab.classList.add('tab-active');
            } else {
                tab.classList.remove('tab-active');
            }
        });
        
        // Show active terminal, hide others
        document.querySelectorAll('.terminal-container').forEach(terminal => {
            if (terminal.id === `terminal-${tabId}`) {
                terminal.classList.remove('hidden');
            } else {
                terminal.classList.add('hidden');
            }
        });
        
        // Focus input
        focusInput(tabId);
    }
    
    // Focus the input of a tab
    function focusInput(tabId) {
        setTimeout(() => {
            const input = document.querySelector(`#terminal-${tabId} .terminal-input`);
            if (input) input.focus();
        }, 0);
    }
    
    // Toggle between light and dark theme
    function toggleTheme() {
        const newTheme = state.theme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme);
    }
    
    // Set a specific theme
    function setTheme(theme) {
        const body = document.body;
        const oldTheme = state.theme;
        state.theme = theme;
        
        // Update theme buttons
        document.querySelectorAll('#theme-selector button').forEach(btn => {
            if (btn.dataset.theme === theme) {
                btn.classList.add('theme-active');
            } else {
                btn.classList.remove('theme-active');
            }
        });
        
        // Apply theme classes
        body.classList.remove(`theme-${oldTheme}`);
        body.classList.add(`theme-${theme}`);
        
        // Apply theme-specific styles
        if (theme === 'light') {
            // Light theme
            body.classList.remove('dark');
            body.style.backgroundColor = 'var(--light-terminal-bg)';
            body.style.color = 'var(--light-terminal-text)';
            
            // Update header and borders
            document.querySelectorAll('header, .border-terminal-border').forEach(el => {
                if (el.classList.contains('bg-terminal-header')) {
                    el.style.backgroundColor = 'var(--light-terminal-header)';
                }
                el.style.borderColor = 'var(--light-terminal-border)';
            });
            
            // Update prompts
            document.querySelectorAll('.terminal-prompt').forEach(el => {
                el.style.color = 'var(--light-terminal-prompt)';
            });
            
            // Update quick command buttons
            document.querySelectorAll('.quick-command, #new-tab-btn, #theme-toggle, #export-logs, #theme-selector button').forEach(el => {
                el.style.backgroundColor = 'var(--light-terminal-border)';
            });
            
        } else if (theme === 'solarized') {
            // Solarized theme
            body.classList.add('dark');
            body.style.backgroundColor = 'var(--solarized-terminal-bg)';
            body.style.color = 'var(--solarized-terminal-text)';
            
            // Update header and borders
            document.querySelectorAll('header, .border-terminal-border').forEach(el => {
                if (el.classList.contains('bg-terminal-header')) {
                    el.style.backgroundColor = 'var(--solarized-terminal-header)';
                }
                el.style.borderColor = 'var(--solarized-terminal-border)';
            });
            
            // Update prompts
            document.querySelectorAll('.terminal-prompt').forEach(el => {
                el.style.color = 'var(--solarized-terminal-prompt)';
            });
            
            // Update quick command buttons
            document.querySelectorAll('.quick-command, #new-tab-btn, #theme-toggle, #export-logs, #theme-selector button').forEach(el => {
                el.style.backgroundColor = 'var(--solarized-terminal-border)';
            });
            
        } else {
            // Default dark theme
            body.classList.add('dark');
            body.style.backgroundColor = 'var(--terminal-bg)';
            body.style.color = 'var(--terminal-text)';
            
            // Update header and borders
            document.querySelectorAll('header, .border-terminal-border').forEach(el => {
                if (el.classList.contains('bg-terminal-header')) {
                    el.style.backgroundColor = 'var(--terminal-header)';
                }
                el.style.borderColor = 'var(--terminal-border)';
            });
            
            // Update prompts
            document.querySelectorAll('.terminal-prompt').forEach(el => {
                el.style.color = 'var(--terminal-prompt)';
            });
            
            // Update quick command buttons
            document.querySelectorAll('.quick-command, #new-tab-btn, #theme-toggle, #export-logs, #theme-selector button').forEach(el => {
                el.style.backgroundColor = 'var(--terminal-border)';
            });
        }
        
        // Save theme preference
        localStorage.setItem('terminal-theme', theme);
    }
    
    // Export logs
    function exportLogs() {
        try {
            const format = confirm('Export as Markdown? (Cancel for plain text)') ? 'md' : 'txt';
            
            // Create a form and submit it (more reliable than window.open)
            const form = document.createElement('form');
            form.method = 'GET';
            form.action = '/api/export-logs';
            form.target = '_blank';
            
            const formatInput = document.createElement('input');
            formatInput.type = 'hidden';
            formatInput.name = 'format';
            formatInput.value = format;
            
            form.appendChild(formatInput);
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
            
        } catch (error) {
            alert('Error exporting logs. Please try again.');
        }
    }
    
    // Update system information in the dashboard
    function updateSystemInfo(data) {
        if (!data) return;
        
        // Update CPU usage
        if (data.cpu) {
            const cpuPercent = data.cpu.percent || 0;
            elements.cpuGauge.style.width = `${cpuPercent}%`;
            elements.cpuText.textContent = `${cpuPercent.toFixed(1)}%`;
            
            // Change color based on usage
            if (cpuPercent > 80) {
                elements.cpuGauge.classList.remove('bg-terminal-prompt', 'bg-yellow-500');
                elements.cpuGauge.classList.add('bg-red-500');
            } else if (cpuPercent > 50) {
                elements.cpuGauge.classList.remove('bg-terminal-prompt', 'bg-red-500');
                elements.cpuGauge.classList.add('bg-yellow-500');
            } else {
                elements.cpuGauge.classList.remove('bg-yellow-500', 'bg-red-500');
                elements.cpuGauge.classList.add('bg-terminal-prompt');
            }
        }
        
        // Update memory usage
        if (data.memory) {
            const memPercent = data.memory.percent || 0;
            elements.memoryGauge.style.width = `${memPercent}%`;
            elements.memoryText.textContent = `${memPercent.toFixed(1)}%`;
            
            // Change color based on usage
            if (memPercent > 80) {
                elements.memoryGauge.classList.remove('bg-blue-500', 'bg-yellow-500');
                elements.memoryGauge.classList.add('bg-red-500');
            } else if (memPercent > 50) {
                elements.memoryGauge.classList.remove('bg-blue-500', 'bg-red-500');
                elements.memoryGauge.classList.add('bg-yellow-500');
            } else {
                elements.memoryGauge.classList.remove('bg-yellow-500', 'bg-red-500');
                elements.memoryGauge.classList.add('bg-blue-500');
            }
        }
        
        // Update process count
        if (data.process_count) {
            elements.processCount.textContent = data.process_count;
        }
    }
    
    // Get welcome message
    function getWelcomeMessage() {
        return `
 _______                    _             _   _____           _           _   
|__   __|                  (_)           | | |  __ \\         (_)         | |  
   | | ___ _ __ _ __ ___    _ _ __   __ _| | | |__) | __ ___  _  ___  ___| |_ 
   | |/ _ \\ '__| '_ \` _ \\  | | '_ \\ / _\` | | |  ___/ '__/ _ \\| |/ _ \\/ __| __|
   | |  __/ |  | | | | | | | | | | | (_| | | | |   | | | (_) | |  __/ (__| |_ 
   |_|\\___|_|  |_| |_| |_| |_|_| |_|\\__,_|_| |_|   |_|  \\___/| |\\___|\\___|\\__|
                                                             _/ |              
                                                            |__/               

Welcome to Terminal Project!
A web-based terminal emulator with Python backend.

Type 'help' to see available commands.
Use '!' prefix for natural language commands (e.g., !create folder logs).

`;
    }
    
    // Load saved theme
    function loadSavedTheme() {
        const savedTheme = localStorage.getItem('terminal-theme');
        if (savedTheme) {
            setTheme(savedTheme);
        }
    }
    
    // Initialize
    initTerminal();
    loadSavedTheme();
});
