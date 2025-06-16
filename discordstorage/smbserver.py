"""
Discord Storage SMB Server
Provides SMB/CIFS network file sharing for Discord Storage
"""

import os
import sys
import time
import threading
import json
import hashlib
import tempfile
import shutil
import socket
import struct
import logging
from datetime import datetime
from typing import Dict, List, Optional

# SMB server dependencies
try:
    from smb.SMBConnection import SMBConnection
    from smb.smb_structs import OperationFailure
    SMB_AVAILABLE = True
except ImportError:
    SMB_AVAILABLE = False
    print("⚠️  SMB libraries not available. Install with: pip install pysmb")

try:
    import smbprotocol
    from smbprotocol.connection import Connection
    from smbprotocol.session import Session
    from smbprotocol.tree import TreeConnect
    SMBPROTOCOL_AVAILABLE = True
except ImportError:
    SMBPROTOCOL_AVAILABLE = False
    print("⚠️  SMBProtocol not available. Install with: pip install smbprotocol")

# Web server for simple file sharing (alternative to SMB)
import cherrypy
import urllib.parse

# Discord Storage imports
from .core import Core


class DiscordWebFileServer:
    """Web-based file server for Discord Storage (simpler alternative to SMB)"""
    
    def __init__(self, core_instance: Core, config_path: str):
        self.core = core_instance
        self.config_path = config_path
        self.files_cache = {}
        self.download_cache = {}
        self.cache_dir = os.path.join(os.getcwd(), "web_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load files from config
        self.reload_file_list()
    
    def reload_file_list(self):
        """Reload file list from config.discord"""
        try:
            with open(self.config_path, 'r') as f:
                first_line = f.readline().strip()
                second_line = f.readline().strip()
                if second_line:
                    self.files_cache = json.loads(second_line)
                else:
                    self.files_cache = {}
        except Exception as e:
            print(f"❌ Error loading file list: {e}")
            self.files_cache = {}
    
    @cherrypy.expose
    def index(self, uploaded=None):
        """Main page showing file list"""
        self.reload_file_list()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Discord Storage Web Interface</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: #fff; }}
                .header {{ background: #5865F2; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                .file-item {{ background: #2f3136; padding: 15px; margin: 10px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }}
                .file-info {{ flex-grow: 1; }}
                .file-name {{ font-size: 16px; font-weight: bold; margin-bottom: 5px; }}
                .file-details {{ font-size: 12px; color: #b9bbbe; }}
                .download-btn {{ background: #5865F2; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; }}
                .download-btn:hover {{ background: #4752C4; }}
                .upload-form {{ background: #2f3136; padding: 20px; border-radius: 10px; margin-top: 20px; }}
                .upload-input {{ width: 100%; padding: 10px; margin: 10px 0; background: #40444b; border: none; color: white; border-radius: 5px; }}
                .upload-btn {{ background: #3ba55c; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
                .upload-btn:hover {{ background: #2d7d32; }}
                .stats {{ background: #36393f; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📦 Discord Storage Web Interface</h1>
                <p>Access your Discord-stored files through this web interface</p>
            </div>
              <div class="stats">
                <strong>📊 Storage Statistics:</strong> {len(self.files_cache)} files stored
            </div>
            """
        
        # Add success message if file was uploaded
        if uploaded:
            html += f"""
            <div style="background: #3ba55c; padding: 15px; border-radius: 8px; margin-bottom: 20px; color: white;">
                <strong>✅ Upload Successful!</strong> File "{uploaded}" has been uploaded to Discord Storage.
            </div>
            """
        
        html += """
            <h2>📁 Stored Files</h2>
        """
        
        if not self.files_cache:
            html += """
            <div class="file-item">
                <div class="file-info">
                    <div class="file-name">No files found</div>
                    <div class="file-details">Upload some files to get started!</div>
                </div>
            </div>
            """
        else:
            for file_code, file_info in self.files_cache.items():
                if file_info and len(file_info) >= 2:
                    filename = file_info[0]
                    file_size = self.format_file_size(file_info[1])
                    hash_info = ""
                    if len(file_info) >= 5:
                        hash_info = f" | Hash: {file_info[4][:8]}..."
                    
                    html += f"""
                    <div class="file-item">
                        <div class="file-info">
                            <div class="file-name">📄 {filename}</div>
                            <div class="file-details">Code: {file_code} | Size: {file_size}{hash_info}</div>
                        </div>
                        <a href="/download/{file_code}" class="download-btn">⬇️ Download</a>
                    </div>
                    """
        
        html += """
            <div class="upload-form">
                <h3>📤 Upload New File</h3>
                <form action="/upload" method="post" enctype="multipart/form-data">
                    <input type="file" name="file" class="upload-input" required>
                    <br>
                    <button type="submit" class="upload-btn">🚀 Upload to Discord</button>
                </form>
            </div>
            
            <div style="margin-top: 40px; text-align: center; color: #72767d;">
                <p>Discord Storage Web Interface | Powered by Discord Storage</p>
                <p><a href="/refresh" style="color: #5865F2;">🔄 Refresh File List</a></p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    @cherrypy.expose
    def refresh(self):
        """Refresh file list and redirect to main page"""
        self.reload_file_list()
        raise cherrypy.HTTPRedirect("/")
    
    @cherrypy.expose
    def download(self, file_code):
        """Download a file"""
        file_info = self.files_cache.get(file_code)
        if not file_info:
            raise cherrypy.HTTPError(404, "File not found")
        
        filename = file_info[0]
          # Check if file is cached
        cache_path = os.path.join(self.cache_dir, f"{file_code}.dat")
        
        if not os.path.exists(cache_path):
            # Download file to cache
            print(f"📥 Downloading {filename} to web cache...")
            try:
                result = self.core.download(file_info)
                if result == -1:
                    raise cherrypy.HTTPError(500, "Failed to download file from Discord")
                
                # Move downloaded file to cache
                downloads_path = os.path.join(self.core.directory, "downloads", filename)
                if os.path.exists(downloads_path):
                    shutil.move(downloads_path, cache_path)
                else:
                    raise cherrypy.HTTPError(500, "Downloaded file not found")
                    
            except Exception as e:
                print(f"❌ Error downloading file: {e}")
                raise cherrypy.HTTPError(500, f"Download error: {str(e)}")
        
        # Serve the cached file
        cherrypy.response.headers['Content-Type'] = 'application/octet-stream'
        cherrypy.response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Read and return file content
        with open(cache_path, 'rb') as f:
            return f.read()
    
    @cherrypy.expose
    def upload(self, file):
        """Upload a file"""
        if not file.filename:
            raise cherrypy.HTTPError(400, "No file selected")
        
        # Save uploaded file to temporary location
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file.filename)
        
        try:
            with open(temp_path, 'wb') as f:
                while True:
                    data = file.file.read(8192)
                    if not data:
                        break
                    f.write(data)
            
            # Generate file code
            file_code = str(abs(hash(file.filename + str(time.time()))) % 10000)
            
            print(f"📤 Uploading {file.filename} to Discord...")
            
            # Upload to Discord
            result = self.core.upload(temp_path, file_code)
            
            if result != -1:
                # Update config file
                self.update_config_with_new_file(file_code, result)
                print(f"✅ File uploaded successfully with code: {file_code}")
                
                # Clean up temp directory first
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                
                # Redirect to main page with success message
                raise cherrypy.HTTPRedirect("/?uploaded=" + file.filename)
            else:
                raise cherrypy.HTTPError(500, "Failed to upload file to Discord")
                
        except cherrypy.HTTPRedirect:
            # Re-raise HTTP redirects (this is the expected behavior)
            raise
        except Exception as e:
            print(f"❌ Upload error: {e}")
            raise cherrypy.HTTPError(500, f"Upload error: {str(e)}")
        finally:
            # Clean up temp directory
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    def update_config_with_new_file(self, file_code: str, file_info: List):
        """Update config.discord with new file"""
        try:
            with open(self.config_path, 'r') as f:
                first_line = f.readline().strip()
                second_line = f.readline().strip()
            
            if second_line:
                files = json.loads(second_line)
            else:
                files = {}
            
            files[file_code] = file_info
            
            with open(self.config_path, 'w') as f:
                f.write(first_line + '\n')
                f.write(json.dumps(files))
            
            self.reload_file_list()
        except Exception as e:
            print(f"❌ Error updating config: {e}")
    
    def format_file_size(self, size):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


class DiscordStorageWebServer:
    """Web server for Discord Storage"""
    
    def __init__(self, core_instance: Core, config_path: str, host: str = '0.0.0.0', port: int = 8080):
        self.core = core_instance
        self.config_path = config_path
        self.host = host
        self.port = port
        self.running = False
        self.server_thread = None
        
        # Create web file server instance
        self.web_app = DiscordWebFileServer(core_instance, config_path)
    
    def start_server(self):
        """Start the web server"""
        if self.running:
            print("⚠️  Web server is already running")
            return
        
        print(f"🚀 Starting Discord Storage Web Server...")
        print(f"📡 Host: {self.host}")
        print(f"🔌 Port: {self.port}")
        print("-" * 50)
        
        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        
        print("✅ Web server started successfully!")
        print(f"🌐 Open in browser: http://{self.host}:{self.port}")
        print("💾 Upload and download files through the web interface")
        print("🔄 To stop the server, press Ctrl+C")
    
    def stop_server(self):
        """Stop the web server"""
        if not self.running:
            return
        
        print("🛑 Stopping web server...")
        self.running = False
        
        try:
            cherrypy.engine.exit()
        except:
            pass
        
        if self.server_thread:
            self.server_thread.join(timeout=5)
        
        print("✅ Web server stopped")
    
    def _run_server(self):
        """Run the web server"""
        try:
            # CherryPy configuration
            cherrypy.config.update({
                'server.socket_host': self.host,
                'server.socket_port': self.port,
                'engine.autoreload.on': False,
                'log.screen': False,
                'log.access_file': '',
                'log.error_file': ''
            })
            
            # Mount the web application
            cherrypy.tree.mount(self.web_app, '/')
            
            # Start the server
            cherrypy.engine.start()
            
            # Keep running until stopped
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Web server error: {e}")
        finally:
            try:
                cherrypy.engine.exit()
            except:
                pass


class DiscordSMBFileSystem:
    """Virtual file system for SMB server backed by Discord Storage"""
    
    def __init__(self, core_instance: Core, config_path: str):
        self.core = core_instance
        self.config_path = config_path
        self.files_cache = {}
        self.cache_dir = os.path.join(os.getcwd(), "smb_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load files from config
        self.reload_file_list()
    
    def reload_file_list(self):
        """Reload file list from config.discord"""
        try:
            with open(self.config_path, 'r') as f:
                first_line = f.readline().strip()
                second_line = f.readline().strip()
                if second_line:
                    self.files_cache = json.loads(second_line)
                else:
                    self.files_cache = {}
        except Exception as e:
            print(f"❌ Error loading file list: {e}")
            self.files_cache = {}
    
    def list_files(self) -> List[Dict]:
        """List all files available in Discord Storage"""
        self.reload_file_list()
        files = []
        
        for file_code, file_info in self.files_cache.items():
            if file_info and len(file_info) >= 2:
                filename = file_info[0]
                file_size = file_info[1]
                
                files.append({
                    'name': filename,
                    'code': file_code,
                    'size': file_size,
                    'is_directory': False,
                    'modified_time': datetime.now(),
                    'created_time': datetime.now()
                })
        
        return files
    
    def get_file_info(self, filename: str) -> Optional[Dict]:
        """Get file information by filename"""
        for file_code, file_info in self.files_cache.items():
            if file_info and len(file_info) >= 2 and file_info[0] == filename:
                return {
                    'name': filename,
                    'code': file_code,
                    'size': file_info[1],
                    'is_directory': False,
                    'modified_time': datetime.now(),
                    'created_time': datetime.now(),
                    'file_info': file_info
                }
        return None
    
    def download_file_to_cache(self, file_info: List, filename: str) -> str:
        """Download file from Discord to local cache and return path"""
        cache_path = os.path.join(self.cache_dir, filename)
        
        if not os.path.exists(cache_path):
            print(f"📥 Downloading {filename} to SMB cache...")
            try:
                result = self.core.download(file_info)
                if result == -1:
                    raise Exception("Failed to download file from Discord")
                
                # Move downloaded file to cache
                downloads_path = os.path.join(self.core.directory, "downloads", filename)
                if os.path.exists(downloads_path):
                    shutil.move(downloads_path, cache_path)
                else:
                    raise Exception("Downloaded file not found")
                    
            except Exception as e:
                print(f"❌ Error downloading file: {e}")
                raise
        
        return cache_path
    
    def upload_file_from_cache(self, local_path: str, filename: str) -> bool:
        """Upload file from local cache to Discord Storage"""
        try:
            # Generate file code
            file_code = str(abs(hash(filename + str(time.time()))) % 10000)
            
            print(f"📤 Uploading {filename} to Discord...")
            
            # Upload to Discord
            result = self.core.upload(local_path, file_code)
            
            if result != -1:
                # Update config file
                self.update_config_with_new_file(file_code, result)
                print(f"✅ File uploaded successfully with code: {file_code}")
                return True
            else:
                print(f"❌ Failed to upload {filename}")
                return False
                
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False
    
    def update_config_with_new_file(self, file_code: str, file_info: List):
        """Update config.discord with new file"""
        try:
            with open(self.config_path, 'r') as f:
                first_line = f.readline().strip()
                second_line = f.readline().strip()
            
            if second_line:
                files = json.loads(second_line)
            else:
                files = {}
            
            files[file_code] = file_info
            
            with open(self.config_path, 'w') as f:
                f.write(first_line + '\n')
                f.write(json.dumps(files))
            
            self.reload_file_list()
        except Exception as e:
            print(f"❌ Error updating config: {e}")
    
    def delete_file(self, filename: str) -> bool:
        """Delete a file from Discord Storage"""
        try:
            # Find the file in our cache
            file_code = None
            for code, info in self.files_cache.items():
                if info[0] == filename:  # info[0] is the filename
                    file_code = code
                    break
            
            if not file_code:
                print(f"❌ File not found in cache: {filename}")
                return False
            
            print(f"🗑️  Deleting {filename} from Discord Storage...")
            
            # Remove from config file
            try:
                with open(self.config_path, 'r') as f:
                    first_line = f.readline().strip()
                    second_line = f.readline().strip()
                
                if second_line:
                    files = json.loads(second_line)
                    if file_code in files:
                        del files[file_code]
                        
                        # Write updated config
                        with open(self.config_path, 'w') as f:
                            f.write(first_line + '\n')
                            f.write(json.dumps(files))
                        
                        # Reload cache
                        self.reload_file_list()
                        
                        print(f"✅ File {filename} deleted from Discord Storage")
                        return True
                    else:
                        print(f"❌ File code {file_code} not found in config")
                        return False
                else:
                    print(f"❌ No files in config")
                    return False
                    
            except Exception as e:
                print(f"❌ Error updating config during delete: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Delete error: {e}")
            return False


class DiscordSMBServer:
    """SMB/CIFS server implementation for Discord Storage"""
    
    def __init__(self, core_instance: Core, config_path: str, 
                 share_name: str = "DiscordStorage", 
                 server_name: str = "DISCORD-STORAGE",
                 host: str = "0.0.0.0", 
                 port: int = 8445):  # Use non-privileged port by default
        
        if not SMB_AVAILABLE and not SMBPROTOCOL_AVAILABLE:
            raise ImportError("SMB libraries not available. Install with: pip install pysmb smbprotocol")
        
        self.core = core_instance
        self.config_path = config_path
        self.share_name = share_name
        self.server_name = server_name
        self.host = host
        self.port = port
        self.running = False
        self.server_thread = None
        
        # Create virtual file system
        self.filesystem = DiscordSMBFileSystem(core_instance, config_path)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # SMB server configuration
        self.smb_config = {
            'server_name': server_name,
            'share_name': share_name,
            'workgroup': 'WORKGROUP',
            'username': 'discord',
            'password': 'storage',
            'allow_anonymous': True
        }
    
    def start_server(self):
        """Start the SMB server"""
        if self.running:
            print("⚠️  SMB server is already running")
            return
        
        print(f"🚀 Starting Discord Storage SMB Server...")
        print(f"📡 Server Name: {self.server_name}")
        print(f"📁 Share Name: {self.share_name}")
        print(f"🌐 Host: {self.host}")
        print(f"🔌 Port: {self.port}")
        if self.port != 445:
            print(f"💡 Using non-standard port {self.port} (standard SMB is 445)")
        print("-" * 50)
        
        self.running = True
        self.server_thread = threading.Thread(target=self._run_smb_server, daemon=True)
        self.server_thread.start()
        
        print("✅ SMB server started successfully!")
        if self.port == 445:
            print(f"🔗 SMB Share: \\\\{self.host}\\{self.share_name}")
        else:
            print(f"🔗 SMB Share: \\\\{self.host}:{self.port}\\{self.share_name}")
        print("💾 Access Discord Storage files through SMB/CIFS")
        print("🔄 To stop the server, press Ctrl+C")
        print("💡 Connection info:")
        print(f"   Username: {self.smb_config['username']}")
        print(f"   Password: {self.smb_config['password']}")
    
    def stop_server(self):
        """Stop the SMB server"""
        if not self.running:
            return
        
        print("🛑 Stopping SMB server...")
        self.running = False
        if self.server_thread:
            self.server_thread.join(timeout=5)
        
        print("✅ SMB server stopped")
    
    def _run_smb_server(self):
        """Run the SMB server using WebDAV protocol for Windows network mapping"""
        try:
            print(f"🎧 Starting WebDAV server on {self.host}:{self.port}")
            print("💡 This provides WebDAV protocol for Windows network mapping")
            
            # Create a WebDAV-compatible HTTP server
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import urllib.parse
            import xml.etree.ElementTree as ET
            from datetime import datetime
            
            filesystem = self.filesystem  # Store reference for the handler
            
            class WebDAVHandler(BaseHTTPRequestHandler):
                def do_OPTIONS(self):
                    """Handle OPTIONS request - required for WebDAV"""
                    self.send_response(200)
                    self.send_header('DAV', '1,2')
                    self.send_header('MS-Author-Via', 'DAV')
                    self.send_header('Allow', 'OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, COPY, MOVE, MKCOL, PROPFIND, PROPPATCH, LOCK, UNLOCK')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                
                def do_PROPFIND(self):
                    """Handle PROPFIND request - WebDAV directory listing"""
                    try:
                        path = urllib.parse.unquote(self.path)
                        depth = self.headers.get('Depth', '1')
                        
                        # Create WebDAV XML response
                        multistatus = ET.Element('multistatus')
                        multistatus.set('xmlns', 'DAV:')
                        
                        if path == '/' or path == '':
                            # Root directory
                            response = ET.SubElement(multistatus, 'response')
                            href = ET.SubElement(response, 'href')
                            href.text = '/'
                            
                            propstat = ET.SubElement(response, 'propstat')
                            prop = ET.SubElement(propstat, 'prop')
                            
                            # Directory properties
                            resourcetype = ET.SubElement(prop, 'resourcetype')
                            ET.SubElement(resourcetype, 'collection')
                            
                            displayname = ET.SubElement(prop, 'displayname')
                            displayname.text = 'DiscordStorage'
                            
                            getlastmodified = ET.SubElement(prop, 'getlastmodified')
                            getlastmodified.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
                            
                            status = ET.SubElement(propstat, 'status')
                            status.text = 'HTTP/1.1 200 OK'
                            
                            # Add files if depth allows
                            if depth != '0':
                                files = filesystem.list_files()
                                for file_info in files:
                                    file_response = ET.SubElement(multistatus, 'response')
                                    file_href = ET.SubElement(file_response, 'href')
                                    file_href.text = f"/{file_info['name']}"
                                    
                                    file_propstat = ET.SubElement(file_response, 'propstat')
                                    file_prop = ET.SubElement(file_propstat, 'prop')
                                    
                                    file_displayname = ET.SubElement(file_prop, 'displayname')
                                    file_displayname.text = file_info['name']
                                    
                                    file_getcontentlength = ET.SubElement(file_prop, 'getcontentlength')
                                    file_getcontentlength.text = str(file_info['size'])
                                    
                                    file_getlastmodified = ET.SubElement(file_prop, 'getlastmodified')
                                    file_getlastmodified.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
                                    
                                    file_getcontenttype = ET.SubElement(file_prop, 'getcontenttype')
                                    file_getcontenttype.text = 'application/octet-stream'
                                    
                                    file_status = ET.SubElement(file_propstat, 'status')
                                    file_status.text = 'HTTP/1.1 200 OK'
                        
                        # Send WebDAV XML response
                        xml_response = ET.tostring(multistatus, encoding='utf-8', xml_declaration=True)
                        
                        self.send_response(207)  # Multi-Status
                        self.send_header('Content-Type', 'text/xml; charset="utf-8"')
                        self.send_header('Content-Length', str(len(xml_response)))
                        self.end_headers()
                        self.wfile.write(xml_response)
                        
                    except Exception as e:
                        print(f"❌ PROPFIND error: {e}")
                        self.send_error(500, str(e))
                
                def do_GET(self):
                    """Handle GET requests for file downloads and directory listings"""
                    try:
                        path = urllib.parse.unquote(self.path)
                        
                        if path == '/' or path == '':                            # Root directory - provide HTML listing for browsers
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html')
                            self.end_headers()
                            
                            # Get host and port info
                            host = filesystem.core.directory  # Placeholder, we'll use a simpler approach
                            
                            html = f"""
                            <!DOCTYPE html>
                            <html>
                            <head><title>Discord Storage WebDAV Share</title></head>
                            <body>
                            <h1>📁 Discord Storage Files</h1>
                            <p>💡 This is a WebDAV share for network mapping</p>
                            <ul>
                            """
                            
                            files = filesystem.list_files()
                            for file_info in files:
                                filename = file_info['name']
                                size = file_info['size']
                                html += f'<li><a href="/{filename}">{filename}</a> ({size} bytes)</li>'
                            
                            html += """
                            </ul>
                            </body>
                            </html>
                            """
                            
                            self.wfile.write(html.encode())
                            
                        else:
                            # File download request
                            filename = path.lstrip('/')
                            file_info = filesystem.get_file_info(filename)
                            
                            if file_info:
                                # Download file to cache and serve it
                                cache_path = filesystem.download_file_to_cache(
                                    file_info['file_info'], filename
                                )
                                
                                self.send_response(200)
                                self.send_header('Content-type', 'application/octet-stream')
                                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                                self.send_header('Content-Length', str(os.path.getsize(cache_path)))
                                self.send_header('Last-Modified', datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))
                                self.end_headers()
                                
                                with open(cache_path, 'rb') as f:
                                    while True:
                                        chunk = f.read(8192)
                                        if not chunk:
                                            break
                                        self.wfile.write(chunk)
                            else:
                                self.send_error(404, "File not found")
                                
                    except Exception as e:
                        print(f"❌ GET Handler error: {e}")
                        self.send_error(500, str(e))
                
                def do_PUT(self):
                    """Handle PUT requests for file uploads"""
                    try:
                        path = urllib.parse.unquote(self.path)
                        filename = path.lstrip('/')
                        
                        if not filename:
                            self.send_error(400, "No filename specified")
                            return
                        
                        content_length = int(self.headers.get('Content-Length', 0))
                        
                        if content_length > 0:
                            print(f"📤 WebDAV: Uploading {filename} ({content_length} bytes)")
                            
                            # Save uploaded file to temporary location
                            temp_dir = tempfile.mkdtemp()
                            temp_path = os.path.join(temp_dir, filename)
                            
                            try:
                                with open(temp_path, 'wb') as f:
                                    remaining = content_length
                                    while remaining > 0:
                                        chunk_size = min(8192, remaining)
                                        chunk = self.rfile.read(chunk_size)
                                        if not chunk:
                                            break
                                        f.write(chunk)
                                        remaining -= len(chunk)
                                
                                # Upload to Discord Storage
                                success = filesystem.upload_file_from_cache(temp_path, filename)
                                
                                if success:
                                    print(f"✅ WebDAV: Upload successful - {filename}")
                                    self.send_response(201)  # Created
                                    self.send_header('Content-Length', '0')
                                    self.end_headers()
                                else:
                                    print(f"❌ WebDAV: Upload failed - {filename}")
                                    self.send_error(500, "Upload to Discord failed")
                                    
                            finally:
                                # Clean up temp directory
                                try:
                                    shutil.rmtree(temp_dir)
                                except:
                                    pass
                        else:
                            # Empty file or directory creation attempt
                            self.send_response(201)  # Created
                            self.send_header('Content-Length', '0')
                            self.end_headers()
                            
                    except Exception as e:
                        print(f"❌ WebDAV PUT error: {e}")
                        self.send_error(500, str(e))
                
                def do_HEAD(self):
                    """Handle HEAD requests - like GET but only headers"""
                    try:
                        path = urllib.parse.unquote(self.path)
                        
                        if path == '/' or path == '':
                            # Root directory
                            self.send_response(200)
                            self.send_header('Content-Type', 'text/html')
                            self.send_header('Content-Length', '1000')  # Approximate
                            self.end_headers()
                        else:
                            # File HEAD request
                            filename = path.lstrip('/')
                            file_info = filesystem.get_file_info(filename)
                            
                            if file_info:
                                self.send_response(200)
                                self.send_header('Content-Type', 'application/octet-stream')
                                self.send_header('Content-Length', str(file_info['size']))
                                self.send_header('Last-Modified', datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))
                                self.end_headers()
                            else:
                                self.send_error(404, "File not found")
                                
                    except Exception as e:
                        print(f"❌ WebDAV HEAD error: {e}")
                        self.send_error(500, str(e))
                
                def do_LOCK(self):
                    """Handle LOCK requests - WebDAV locking (simplified)"""
                    try:
                        # Simple lock response - we'll allow all locks for now
                        lock_token = f"urn:uuid:{hash(self.path + str(time.time())) % 1000000}"
                        
                        lock_response = f'''<?xml version="1.0" encoding="utf-8"?>
<prop xmlns="DAV:">
    <lockdiscovery>
        <activelock>
            <locktype><write/></locktype>
            <lockscope><exclusive/></lockscope>
            <depth>0</depth>
            <owner>Discord Storage</owner>
            <timeout>Second-3600</timeout>
            <locktoken><href>{lock_token}</href></locktoken>
        </activelock>
    </lockdiscovery>
</prop>'''
                        
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/xml; charset="utf-8"')
                        self.send_header('Lock-Token', f'<{lock_token}>')
                        self.send_header('Content-Length', str(len(lock_response)))
                        self.end_headers()
                        self.wfile.write(lock_response.encode('utf-8'))
                        
                    except Exception as e:
                        print(f"❌ WebDAV LOCK error: {e}")
                        self.send_error(500, str(e))
                
                def do_UNLOCK(self):
                    """Handle UNLOCK requests - WebDAV unlocking"""
                    try:
                        # Simple unlock response - always successful
                        self.send_response(204)  # No Content
                        self.send_header('Content-Length', '0')
                        self.end_headers()
                        
                    except Exception as e:
                        print(f"❌ WebDAV UNLOCK error: {e}")
                        self.send_error(500, str(e))
                
                def do_PROPPATCH(self):
                    """Handle PROPPATCH requests - property modification"""
                    try:
                        # Simple property patch response - claim success for basic properties
                        proppatch_response = '''<?xml version="1.0" encoding="utf-8"?>
<multistatus xmlns="DAV:">
    <response>
        <href>{}</href>
        <propstat>
            <status>HTTP/1.1 200 OK</status>
        </propstat>
    </response>
</multistatus>'''.format(self.path)
                        
                        self.send_response(207)  # Multi-Status
                        self.send_header('Content-Type', 'text/xml; charset="utf-8"')
                        self.send_header('Content-Length', str(len(proppatch_response)))
                        self.end_headers()
                        self.wfile.write(proppatch_response.encode('utf-8'))
                        
                    except Exception as e:
                        print(f"❌ WebDAV PROPPATCH error: {e}")
                        self.send_error(500, str(e))
                
                def do_MOVE(self):
                    """Handle MOVE requests - WebDAV file/folder renaming and moving"""
                    try:
                        source_path = urllib.parse.unquote(self.path)
                        source_filename = source_path.lstrip('/')
                        
                        # Get destination from Destination header
                        destination_header = self.headers.get('Destination', '')
                        if not destination_header:
                            self.send_error(400, "Missing Destination header")
                            return
                        
                        # Parse destination URL
                        from urllib.parse import urlparse
                        dest_url = urlparse(destination_header)
                        dest_path = urllib.parse.unquote(dest_url.path)
                        dest_filename = dest_path.lstrip('/')
                        
                        if not source_filename or not dest_filename:
                            self.send_error(400, "Invalid source or destination path")
                            return
                        
                        print(f"🔄 WebDAV: Moving/Renaming '{source_filename}' to '{dest_filename}'")
                        
                        # Check if source file exists
                        source_file_info = filesystem.get_file_info(source_filename)
                        if not source_file_info:
                            self.send_error(404, "Source file not found")
                            return
                        
                        # Download source file to temporary location
                        temp_dir = tempfile.mkdtemp()
                        try:
                            temp_source_path = filesystem.download_file_to_cache(
                                source_file_info['file_info'], source_filename
                            )
                            
                            # Create renamed file in temp directory
                            temp_dest_path = os.path.join(temp_dir, dest_filename)
                            shutil.copy2(temp_source_path, temp_dest_path)
                            
                            # Upload renamed file to Discord
                            success = filesystem.upload_file_from_cache(temp_dest_path, dest_filename)
                            
                            if success:
                                # Delete the old file from Discord Storage
                                delete_success = filesystem.delete_file(source_filename)
                                
                                if delete_success:
                                    print(f"✅ WebDAV: Successfully moved '{source_filename}' to '{dest_filename}'")
                                    self.send_response(201)  # Created (new resource)
                                    self.send_header('Content-Length', '0')
                                    self.end_headers()
                                else:
                                    print(f"⚠️  WebDAV: Uploaded new file but failed to delete old file")
                                    self.send_response(201)  # Still consider it success
                                    self.send_header('Content-Length', '0') 
                                    self.end_headers()
                            else:
                                print(f"❌ WebDAV: Failed to upload renamed file")
                                self.send_error(500, "Failed to upload renamed file")
                                
                        finally:
                            # Clean up temp directory
                            try:
                                shutil.rmtree(temp_dir)
                            except:
                                pass
                                
                    except Exception as e:
                        print(f"❌ WebDAV MOVE error: {e}")
                        self.send_error(500, str(e))
                
                def do_COPY(self):
                    """Handle COPY requests - WebDAV file copying"""
                    try:
                        source_path = urllib.parse.unquote(self.path)
                        source_filename = source_path.lstrip('/')
                        
                        # Get destination from Destination header
                        destination_header = self.headers.get('Destination', '')
                        if not destination_header:
                            self.send_error(400, "Missing Destination header")
                            return
                        
                        # Parse destination URL
                        from urllib.parse import urlparse
                        dest_url = urlparse(destination_header)
                        dest_path = urllib.parse.unquote(dest_url.path)
                        dest_filename = dest_path.lstrip('/')
                        
                        if not source_filename or not dest_filename:
                            self.send_error(400, "Invalid source or destination path")
                            return
                        
                        print(f"📋 WebDAV: Copying '{source_filename}' to '{dest_filename}'")
                        
                        # Check if source file exists
                        source_file_info = filesystem.get_file_info(source_filename)
                        if not source_file_info:
                            self.send_error(404, "Source file not found")
                            return
                        
                        # Download source file to temporary location
                        temp_dir = tempfile.mkdtemp()
                        try:
                            temp_source_path = filesystem.download_file_to_cache(
                                source_file_info['file_info'], source_filename
                            )
                            
                            # Create copy in temp directory
                            temp_dest_path = os.path.join(temp_dir, dest_filename)
                            shutil.copy2(temp_source_path, temp_dest_path)
                            
                            # Upload copy to Discord
                            success = filesystem.upload_file_from_cache(temp_dest_path, dest_filename)
                            
                            if success:
                                print(f"✅ WebDAV: Successfully copied '{source_filename}' to '{dest_filename}'")
                                self.send_response(201)  # Created
                                self.send_header('Content-Length', '0')
                                self.end_headers()
                            else:
                                print(f"❌ WebDAV: Failed to upload copied file")
                                self.send_error(500, "Failed to upload copied file")
                                
                        finally:
                            # Clean up temp directory
                            try:
                                shutil.rmtree(temp_dir)
                            except:
                                pass
                                
                    except Exception as e:
                        print(f"❌ WebDAV COPY error: {e}")
                        self.send_error(500, str(e))
                
                def do_MKCOL(self):
                    """Handle MKCOL requests (create directory) - not supported"""
                    self.send_error(405, "Directory creation not supported")
                
                def do_DELETE(self):
                    """Handle DELETE requests - WebDAV file deletion"""
                    try:
                        path = urllib.parse.unquote(self.path)
                        filename = path.lstrip('/')
                        
                        if not filename:
                            self.send_error(400, "No filename specified")
                            return
                        
                        print(f"🗑️  WebDAV: Deleting '{filename}'")
                        
                        # Check if file exists
                        file_info = filesystem.get_file_info(filename)
                        if not file_info:
                            self.send_error(404, "File not found")
                            return
                        
                        # Delete the file
                        success = filesystem.delete_file(filename)
                        
                        if success:
                            print(f"✅ WebDAV: Successfully deleted '{filename}'")
                            self.send_response(204)  # No Content
                            self.send_header('Content-Length', '0')
                            self.end_headers()
                        else:
                            print(f"❌ WebDAV: Failed to delete '{filename}'")
                            self.send_error(500, "Failed to delete file")
                            
                    except Exception as e:
                        print(f"❌ WebDAV DELETE error: {e}")
                        self.send_error(500, str(e))
                
                def log_message(self, format, *args):
                    """Override to reduce logging noise"""
                    if self.path not in ['/', '/favicon.ico']:
                        print(f"📡 WebDAV: {self.command} {self.path}")
            
            # Create HTTP server with WebDAV support
            server = HTTPServer((self.host, self.port), WebDAVHandler)
            server.timeout = 1  # 1 second timeout for handle_request
            server.server_name = self.host
            server.server_port = self.port
            
            print(f"✅ WebDAV server ready for network mapping!")
            print(f"🔗 Network path: \\\\{self.host}:{self.port}\\{self.share_name}")
            print(f"🌐 Browser access: http://{self.host}:{self.port}")
            
            # Keep running until stopped
            while self.running:
                server.handle_request()
                
        except Exception as e:
            print(f"❌ WebDAV server error: {e}")
            if "Permission denied" in str(e) or "WinError 10013" in str(e):
                print("💡 Try using a different port or run as administrator")
        finally:
            try:
                server.server_close()
            except:
                pass


class DiscordStorageUnifiedServer:
    """Unified server supporting both SMB and Web interfaces"""
    
    def __init__(self, core_instance: Core, config_path: str):
        self.core = core_instance
        self.config_path = config_path
        self.running = False
        
        # Server instances
        self.web_server = None
        self.smb_server = None
        
        # Configuration
        self.web_enabled = True
        self.smb_enabled = SMB_AVAILABLE or SMBPROTOCOL_AVAILABLE
        
        print(f"🔧 Unified Server Configuration:")
        print(f"   📡 Web Server: {'✅ Available' if self.web_enabled else '❌ Disabled'}")
        print(f"   📁 SMB Server: {'✅ Available' if self.smb_enabled else '❌ Not Available'}")
    
    def start_servers(self, 
                     web_enabled: bool = True,
                     web_host: str = '127.0.0.1', 
                     web_port: int = 8080,
                     smb_enabled: bool = True,
                     smb_host: str = '0.0.0.0',
                     smb_port: int = 445,
                     smb_share_name: str = 'DiscordStorage',
                     smb_server_name: str = 'DISCORD-STORAGE'):
        """Start all configured servers"""
        
        if self.running:
            print("⚠️  Servers are already running")
            return
        
        self.running = True
        
        print("🚀 Starting Discord Storage Unified Server...")
        print("=" * 60)
          # Start Web Server
        if self.web_enabled and web_enabled:
            try:
                self.web_server = DiscordStorageWebServer(
                    self.core, self.config_path, web_host, web_port
                )
                self.web_server.start_server()
                print(f"✅ Web Server started on http://{web_host}:{web_port}")
            except Exception as e:
                print(f"❌ Failed to start Web Server: {e}")
        
        # Start SMB Server
        if self.smb_enabled and smb_enabled:
            try:
                self.smb_server = DiscordSMBServer(
                    self.core, self.config_path, 
                    smb_share_name, smb_server_name, smb_host, smb_port
                )
                self.smb_server.start_server()
                print(f"✅ SMB Server started on \\\\{smb_host}\\{smb_share_name}")
            except Exception as e:
                print(f"❌ Failed to start SMB Server: {e}")
                print("💡 Note: SMB server requires administrator privileges on Windows")
        
        print("=" * 60)
        print("🎉 Discord Storage servers are now running!")
        print()
        print("📡 Access Methods:")
        if self.web_server:
            print(f"   🌐 Web Interface: http://{web_host}:{web_port}")
        if self.smb_server:
            print(f"   📁 SMB Share: \\\\{smb_host}\\{smb_share_name}")
            print("   💡 SMB Usage:")
            print("      - Windows: Open File Explorer, go to Network, or type the path")
            print("      - Linux: Use smbclient or mount the share")
            print("      - macOS: Use Finder > Go > Connect to Server")
        print()
        print("🔄 To stop all servers, press Ctrl+C")
    
    def stop_servers(self):
        """Stop all running servers"""
        if not self.running:
            return
        
        print("🛑 Stopping all servers...")
        self.running = False
        
        if self.web_server:
            self.web_server.stop_server()
        
        if self.smb_server:
            self.smb_server.stop_server()
        
        print("✅ All servers stopped")
    
    def get_server_status(self):
        """Get status of all servers"""
        status = {
            'running': self.running,
            'web_server': {
                'enabled': self.web_enabled,
                'running': self.web_server.running if self.web_server else False,
                'host': self.web_server.host if self.web_server else None,
                'port': self.web_server.port if self.web_server else None
            },
            'smb_server': {
                'enabled': self.smb_enabled,
                'running': self.smb_server.running if self.smb_server else False,
                'host': self.smb_server.host if self.smb_server else None,
                'port': self.smb_server.port if self.smb_server else None,
                'share_name': self.smb_server.share_name if self.smb_server else None
            }
        }
        return status


def create_web_server(token: str, channel_id: str, host: str = '0.0.0.0', port: int = 8080) -> DiscordStorageWebServer:
    """Create and configure web server"""
    # Create Discord core instance
    core_instance = Core(os.getcwd() + "/", token, channel_id)
    
    # Path to config file
    config_path = os.path.join(os.getcwd(), "config.discord")
    
    # Create web server
    web_server = DiscordStorageWebServer(core_instance, config_path, host, port)
    
    return web_server


def start_web_server_standalone(token: str, channel_id: str, host: str = '0.0.0.0', port: int = 8080):
    """Start web server in standalone mode"""
    print("🏗️  Setting up Discord Storage Web Server...")
    
    # Create and start web server
    web_server = create_web_server(token, channel_id, host, port)
    
    # Start Discord connection
    print("🔌 Starting Discord connection...")
    discord_thread = threading.Thread(target=web_server.core.start, daemon=True)
    discord_thread.start()
    
    # Wait for Discord to be ready
    print("⏳ Waiting for Discord connection...")
    while not web_server.core.isready():
        time.sleep(1)
    
    print("✅ Discord connection established!")
    
    # Start web server
    web_server.start_server()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down web server...")
        web_server.stop_server()
        print("✅ Web server shut down complete")


def create_unified_server(token: str, channel_id: str) -> DiscordStorageUnifiedServer:
    """Create unified server with both web and SMB capabilities"""
    # Create Discord core instance
    core_instance = Core(os.getcwd() + "/", token, channel_id)
    
    # Path to config file
    config_path = os.path.join(os.getcwd(), "config.discord")
    
    # Create unified server
    unified_server = DiscordStorageUnifiedServer(core_instance, config_path)
    
    return unified_server


def start_unified_server_standalone(token: str, channel_id: str, 
                                   web_enabled: bool = True,
                                   web_host: str = '127.0.0.1', 
                                   web_port: int = 8080,
                                   smb_enabled: bool = True,
                                   smb_host: str = '0.0.0.0',
                                   smb_port: int = 445):
    """Start unified server with both web and SMB in standalone mode"""
    print("🏗️  Setting up Discord Storage Unified Server...")
    
    # Create unified server
    unified_server = create_unified_server(token, channel_id)
    
    # Start Discord connection
    print("🔌 Starting Discord connection...")
    discord_thread = threading.Thread(target=unified_server.core.start, daemon=True)
    discord_thread.start()
    
    # Wait for Discord to be ready
    print("⏳ Waiting for Discord connection...")
    while not unified_server.core.isready():
        time.sleep(1)
    
    print("✅ Discord connection established!")
      # Start all servers
    unified_server.start_servers(
        web_enabled=web_enabled,
        web_host=web_host, 
        web_port=web_port,
        smb_enabled=smb_enabled,
        smb_host=smb_host,
        smb_port=smb_port
    )
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down unified server...")
        unified_server.stop_servers()
        print("✅ Unified server shutdown complete")


# Legacy function names for compatibility
start_smb_server_standalone = start_web_server_standalone
create_smb_server = create_web_server
