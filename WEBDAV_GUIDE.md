# 🌐 WebDAV Network Drive Mapping Guide

## ✅ **Enhanced WebDAV Support**

Your Discord Storage SMB server now supports **WebDAV protocol**, which Windows can properly recognize and map as a network drive!

## 🖥️ **Windows Network Drive Mapping**

### **Method 1: Map Network Drive (Recommended)**

1. **Open File Explorer**
2. **Right-click "This PC"** → **"Map network drive..."**
3. **Enter the WebDAV URL:**
   ```
   http://127.0.0.1:12345/
   ```
   *(Replace 12345 with your chosen port)*

4. **Check "Connect using different credentials"** if prompted
5. **Click "Finish"**

### **Method 2: Add Network Location**

1. **Open File Explorer**
2. **Right-click "This PC"** → **"Add a network location"**
3. **Choose "Choose a custom network location"**
4. **Enter the WebDAV URL:**
   ```
   http://127.0.0.1:12345/
   ```
5. **Follow the wizard to complete setup**

### **Method 3: Direct Navigation**

1. **Open File Explorer**
2. **Type in address bar:**
   ```
   \\127.0.0.1@12345\DavWWWRoot
   ```

## 🐧 **Linux WebDAV Access**

```bash
# Install davfs2
sudo apt-get install davfs2

# Create mount point
sudo mkdir /mnt/discord-storage

# Mount WebDAV share
sudo mount -t davfs http://127.0.0.1:12345/ /mnt/discord-storage

# Access files
ls /mnt/discord-storage
```

## 🍎 **macOS WebDAV Access**

1. **Open Finder**
2. **Press Cmd+K** (Connect to Server)
3. **Enter server address:**
   ```
   http://127.0.0.1:12345/
   ```
4. **Click "Connect"**

## 🔧 **WebDAV Features Supported**

- ✅ **Directory Listing** (PROPFIND)
- ✅ **File Download** (GET)
- ✅ **File Upload** (PUT)
- ✅ **WebDAV Discovery** (OPTIONS)
- ✅ **Metadata Properties** (file size, dates)
- ✅ **Cross-platform Compatibility**

## 🚀 **Starting WebDAV Server**

```bash
python ds.py -s
# Select option 2 (SMB Server Only) or 3 (Unified)
# Choose your port (e.g., 12345)
```

**Output will show:**
```
🎧 Starting WebDAV server on 127.0.0.1:12345
💡 This provides WebDAV protocol for Windows network mapping
✅ WebDAV server ready for network mapping!
🔗 Network path: \\127.0.0.1:12345\DiscordStorage
🌐 Browser access: http://127.0.0.1:12345
```

## 🛠️ **Troubleshooting**

### **Issue: "The network folder specified is not valid"**
- **Solution**: Use `http://` prefix in the URL
- **Try**: `http://127.0.0.1:12345/` instead of `\\127.0.0.1:12345`

### **Issue: Authentication prompts**
- **Username**: `discord`
- **Password**: `storage`
- *(Currently not enforced, but may be requested by Windows)*

### **Issue: Can't map drive**
- **Enable WebDAV client service:**
  1. Press Win+R, type `services.msc`
  2. Find "WebClient" service
  3. Set to "Automatic" and Start it
  4. Restart and try again

### **Issue: Port already in use**
- **Choose a different port** (e.g., 8445, 9090, 12345)
- **Avoid privileged ports** (below 1024)

## 📁 **File Operations Supported**

| Operation | WebDAV Method | Status |
|-----------|---------------|--------|
| Browse files | PROPFIND | ✅ Supported |
| Download files | GET | ✅ Supported |
| Upload files | PUT | ✅ Supported |
| **Rename files** | **MOVE** | **✅ Supported** |
| **Copy files** | **COPY** | **✅ Supported** |
| **Delete files** | **DELETE** | **✅ Supported** |
| Create folders | MKCOL | ❌ Not implemented |
| File locking | LOCK/UNLOCK | ✅ Supported |

### 🔄 **File Management Features**

#### **✅ Renaming Files**
- **Right-click** a file in the mapped drive
- **Select "Rename"** or press F2
- **Type new name** and press Enter
- File is automatically **re-uploaded to Discord** with new name
- **Old file is deleted** from Discord Storage

#### **✅ Copying Files**
- **Ctrl+C** to copy a file
- **Ctrl+V** to paste in the same or different location
- **Creates duplicate** on Discord Storage with new name

#### **✅ Deleting Files**
- **Right-click** a file and select **"Delete"**
- **Press Delete key** on selected file
- **File is removed** from Discord Storage permanently

#### **✅ File Upload (Drag & Drop)**
- **Drag files** from local folders to mapped drive
- **Copy files** using Ctrl+C/Ctrl+V
- **Move files** between local and Discord Storage

### 🎯 **Advanced WebDAV Operations**

#### **File Locking**
- Windows automatically **locks files** during operations
- **Prevents conflicts** during upload/rename operations
- **Automatic unlocking** when operation completes

#### **Metadata Support**
- **File sizes** displayed correctly
- **Modification dates** preserved
- **MIME types** for proper file handling

## 🎉 **Success!**

Once mapped, you can:
- **Browse** Discord Storage files like any network drive
- **Download** files by copying them locally
- **Upload** files by copying them to the mapped drive
- **✨ Rename** files using F2 or right-click menu
- **✨ Copy** files using Ctrl+C/Ctrl+V
- **✨ Delete** files using Delete key or right-click menu
- **✨ Drag & drop** files for easy upload
- **Access** from any application that supports network drives

**Example mapped drive path:** `Z:\` (or whatever letter Windows assigns)

### 🚀 **Full File Management**
Your Discord Storage now works like any regular network drive with **complete file management capabilities**:

- **File Explorer integration** - Works with Windows File Explorer
- **Application support** - Open files directly from mapped drive
- **Context menu support** - Right-click operations work
- **Keyboard shortcuts** - F2 (rename), Delete, Ctrl+C/V, etc.
- **Drag & drop support** - Move files easily
- **Real-time updates** - Changes reflect immediately

Your Discord Storage is now a **fully functional network drive**! 🚀🎊
