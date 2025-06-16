# Discord Storage 📦

Transform Discord servers into your personal cloud storage! Upload, download, and manage files using Discord's infrastructure with advanced features like file recovery, hash verification, and smart resume capabilities.

## ✨ Features

- 🚀 **Upload/Download Files** - Store any file type on Discord servers
- 🌐 **Web Server Interface** - Access your files through a web browser with built-in file manager
- 🔄 **File Recovery** - Recover lost files using Discord URLs (even without config file!)
- 🔐 **Hash Verification** - Ensure file integrity with MD5 hash checking
- 📊 **Progress Tracking** - Real-time upload/download progress with speed monitoring
- ⚡ **Smart Resume** - Resume interrupted uploads/downloads automatically
- 🔍 **File Type Detection** - Automatic file type detection and extension guessing
- 📋 **File Management** - List and manage all your stored files
- 🎯 **Large File Support** - Handles files of any size with chunking (9MB per chunk)

## 🛠️ Requirements

- **Python 3.11+** (Tested on Python 3.11)
- **Discord Bot Token** 
- **Discord Server/Channel** with bot access

## 📥 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/cyberofficial/DiscordStorage.git
   cd DiscordStorage
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the program** (first-time setup)
   ```bash
   python ds.py
   ```

## 🤖 Discord Bot Setup

### 1) Create a Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section in the sidebar
4. Click "Add Bot" and confirm
5. **Copy the bot token** (keep this secret!)
6. **Copy the Application ID** from the "General Information" tab

### 2) Create a Discord Server
- Create a new Discord server for file storage
- Make it private (don't share with others unless you want them to access your files)

### 3) Add Bot to Server
Visit this URL (replace `{CLIENT_ID}` with your Application ID):
```
https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&scope=bot&permissions=274877906944
```

### 4) Get Channel ID
1. Enable Developer Mode in Discord (Settings → Appearance → Developer Mode)
2. Right-click on your channel → "Copy Channel ID"

## 📖 Usage

### Initial Configuration
Run `python ds.py` and enter:
- Your bot token
- Channel ID where files will be stored

### Commands

#### 📤 Upload Files
```bash
python ds.py -u /path/to/your/file.ext
python ds.py -upload C:\Users\YourName\Documents\video.mp4
```

#### 📥 Download Files
```bash
python ds.py -d FILE_CODE
python ds.py -download 1234
```

#### 📋 List Files
```bash
python ds.py -l
python ds.py -list
```

#### 🔄 **File Recovery** (NEW!)
Recover files even if you lost your `config.discord` file:
```bash
python ds.py -r FILE_ID HASH_URL CHUNK_URL1 [CHUNK_URL2] ...
python ds.py -recover 3002 "https://cdn.discordapp.com/..." "https://cdn.discordapp.com/..."
```

#### 🌐 **Web Server** (NEW!)
Start a web server to access your Discord storage through a browser:
```bash
python ds.py -s
python ds.py -smb
python ds.py -samba
```

#### ❓ Help
```bash
python ds.py -h
python ds.py -help
```

## 🔧 Advanced Features

### Web Server Interface
Access your Discord storage through a modern web browser:
- **📱 Responsive Design** - Works on desktop, tablet, and mobile
- **📤 Drag & Drop Upload** - Simply drag files to upload
- **📥 One-Click Download** - Download files with a single click
- **📊 Storage Statistics** - View file count and storage usage
- **🔄 Real-time Updates** - Automatically refreshes file list
- **🎨 Dark Theme** - Easy on the eyes with Discord-inspired design

### File Recovery System
Lost your config file? No problem! The recovery system can:
- Download files using Discord CDN URLs
- Verify file integrity with hash checking
- Automatically detect file types and suggest extensions
- Add recovered files back to your config database
- Handle expired Discord URLs with helpful guidance

### Smart File Type Detection
- Automatically downloads Windows file utility for type detection
- Recognizes 60+ file formats
- Suggests appropriate file extensions
- Allows manual extension override

### Progress & Resume
- Visual progress bars with speed monitoring
- Automatic resume for interrupted transfers
- Chunk-based uploading for reliability
- ETA calculations and performance metrics

## 🔒 Security & Privacy

- Bot tokens are stored locally in `config.discord`
- Files are stored on Discord's CDN (subject to Discord's terms)
- MD5 hash verification ensures file integrity
- No third-party servers involved

## 📁 File Structure

```
DiscordStorage/
├── ds.py                 # Main application
├── discordstorage/       # Core modules
│   ├── core.py          # Upload/download logic
│   └── Session.py       # Discord API wrapper
├── config.discord       # Configuration file (auto-generated)
├── downloads/           # Downloaded files
├── recovery/            # Temporary recovery files
├── uploading/           # Temporary upload chunks
└── downloading/         # Temporary download chunks
```

## 🚨 Important Notes

- **Discord ToS**: This tool uses Discord as storage. Use responsibly and within Discord's Terms of Service
- **File Limits**: Individual files are chunked into 9MB pieces (Discord Nitro users could modify for 50MB chunks)
- **Reliability**: While reliable, this shouldn't be your only backup solution
- **URLs Expire**: Discord CDN URLs expire after some time, but recovery URLs can be refreshed

## 🙏 Credits & Attribution

This project is a fork and enhancement of the original [DiscordStorage](https://github.com/nigel/DiscordStorage) by [nigel](https://github.com/nigel).

**Original Project**: https://github.com/nigel/DiscordStorage  
**Enhanced Fork**: https://github.com/cyberofficial/DiscordStorage

### Major Enhancements Added:
- **Web Server Interface** - Access Discord storage through a modern web browser
- File recovery system with URL-based restoration
- Advanced hash verification and file integrity checks
- Smart resume capabilities for interrupted transfers
- Automatic file type detection and extension guessing
- Enhanced progress tracking and user experience
- Improved error handling and troubleshooting guidance
- Modern Python 3.11+ compatibility

Special thanks to the original author for creating the foundation of this project!

## 📄 License

This project maintains the same license as the original project. Please refer to the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for educational and personal use. Users are responsible for complying with Discord's Terms of Service and applicable laws. The authors are not responsible for any misuse or violations.



