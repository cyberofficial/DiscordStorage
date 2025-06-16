#!/usr/bin/env python3
"""
Test script to verify SMB/HTTP file server functionality
"""

import requests
import os
import sys

def test_smb_http_server(host="127.0.0.1", port=8445):
    """Test the HTTP-based SMB server functionality"""
    
    base_url = f"http://{host}:{port}"
    
    print(f"🧪 Testing Discord Storage SMB/HTTP Server")
    print(f"📡 Server: {base_url}")
    print("=" * 50)
    
    try:
        # Test 1: Check if server is accessible
        print("1. Testing server connectivity...")
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("✅ Server is accessible")
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
            
        # Test 2: Check file listing
        print("2. Testing file listing...")
        if "Discord Storage Files" in response.text:
            print("✅ File listing page loads correctly")
        else:
            print("❌ File listing page format incorrect")
            return False
            
        # Test 3: Check for any files
        print("3. Checking for available files...")
        if "<li>" in response.text and ".html" not in response.text:
            print("✅ Files are available for download")
        else:
            print("💡 No files currently stored (this is normal for new installations)")
            
        print("\n🎉 SMB/HTTP server is working correctly!")
        print(f"🌐 Access via browser: {base_url}")
        print("📁 You can now map this as a network drive or access via browser")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server")
        print("💡 Make sure the server is running")
        return False
    except requests.exceptions.Timeout:
        print("❌ Server connection timed out")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def show_network_mapping_instructions(host="127.0.0.1", port=8445):
    """Show instructions for mapping the server as a network drive"""
    
    print("\n📁 Network Drive Mapping Instructions:")
    print("=" * 50)
    print("🖥️  Windows:")
    print(f"   1. Open File Explorer")
    print(f"   2. Right-click 'This PC' → 'Map network drive'")
    print(f"   3. Enter: http://{host}:{port}")
    print(f"   4. Or manually navigate to: {host}:{port} in browser")
    print()
    print("🐧 Linux:")
    print(f"   1. Use curl: curl http://{host}:{port}")
    print(f"   2. Or mount with davfs2 (if WebDAV support added)")
    print()
    print("🍎 macOS:")
    print(f"   1. Finder → Go → Connect to Server")
    print(f"   2. Enter: http://{host}:{port}")
    print()
    print("💡 Note: This is an HTTP-based file server, not true SMB/CIFS")
    print("   It provides similar functionality for accessing Discord Storage files")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8445
    
    if len(sys.argv) > 2:
        host = sys.argv[2]
    else:
        host = "127.0.0.1"
    
    success = test_smb_http_server(host, port)
    
    if success:
        show_network_mapping_instructions(host, port)
    else:
        print("\n💡 Troubleshooting:")
        print("   - Make sure the Discord Storage server is running")
        print("   - Try: python ds.py -s")
        print("   - Select option 2 or 3 for SMB server")
        print(f"   - Use port {port} when configuring")
