# Web-Based Terminal Project

A modern, feature-rich terminal emulator built with Python Flask and JavaScript, offering a seamless web-based command-line experience.

## 🚀 Features

LIVE DEMO = python-terminal.vercel.app

- **Interactive Terminal Interface**
  - Real-time command execution
  - Command history navigation
  - Intelligent autocomplete
  - Multi-tab support

- **System Monitoring**
  - Real-time CPU usage
  - Memory consumption tracking
  - Active process monitoring
  - Live system statistics

- **User Experience**
  - Dark/Light/Solarized themes
  - Quick Commands Panel
  - Command history persistence
  - Export logs functionality

- **Developer Tools**
  - Natural language command interpretation
  - Command suggestions
  - Error handling with smart corrections
  - Session management

## 🛠️ Technology Stack

- **Backend**
  - Python 3.x
  - Flask
  - Flask-SocketIO
  - Eventlet
  - psutil

- **Frontend**
  - HTML5/CSS3
  - JavaScript
  - TailwindCSS
  - Socket.IO client

## ⚙️ Installation

1. **Clone the repository**
```bash
git clone https://github.com/arvindpandey4/terminal_project.git
cd terminal_project
```

2. **Set up virtual environment**
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

## 🚀 Usage

1. **Start the application**
```bash
python main.py
```

2. **Access the terminal**
- Open your browser
- Navigate to: `http://localhost:5000`

## 💻 Available Commands

- `ls` - List directory contents
- `cd` - Change directory
- `pwd` - Print working directory
- `mkdir` - Create directory
- `rm` - Remove files/directories
- `cp` - Copy files
- `mv` - Move files
- `cpu` - Show CPU information
- `memory` - Display memory usage
- `processes` - List running processes
- `help` - Show all commands

## 🎨 Themes

Switch between themes using the theme toggle button:
- Dark Theme (Default)
- Light Theme
- Solarized Theme

## 📋 Quick Commands

Access frequently used commands via the Quick Commands panel:
- Create Folder
- List Files
- Clear Terminal
- System Information
- Process List

## 📄 License

MIT License

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request
