#!/usr/bin/env python3
"""
Discord Storage Web Server Demo
Quick test to see if the web server functionality works
"""

import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_web_server_import():
    """Test if we can import the web server module"""
    try:
        from discordstorage.smbserver import DiscordWebFileServer, DiscordStorageWebServer
        print("✅ Web server modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import web server modules: {e}")
        return False

def test_dependencies():
    """Test if required dependencies are available"""
    dependencies = ['cherrypy', 'discord', 'aiohttp']
    missing = []
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep} is available")
        except ImportError:
            print(f"❌ {dep} is missing")
            missing.append(dep)
    
    return len(missing) == 0

def mock_core_test():
    """Create a mock Core instance for testing"""
    try:
        from discordstorage.core import Core
        
        # Test creating a Core instance (won't actually connect without valid token)
        core = Core("./", "mock_token", "mock_channel")
        print("✅ Core class can be instantiated")
        return True
    except Exception as e:
        print(f"❌ Failed to create Core instance: {e}")
        return False

def main():
    print("🧪 Discord Storage Web Server Test")
    print("=" * 50)
    
    print("\n1. Testing dependencies...")
    deps_ok = test_dependencies()
    
    print("\n2. Testing web server import...")
    import_ok = test_web_server_import()
    
    print("\n3. Testing core functionality...")
    core_ok = mock_core_test()
    
    print("\n" + "=" * 50)
    if deps_ok and import_ok and core_ok:
        print("🎉 All tests passed! Web server should work.")
        print("\n💡 To start the web server:")
        print("   python ds.py -s")
        print("\n🌐 Then visit http://localhost:8080 in your browser")
    else:
        print("❌ Some tests failed. Check the errors above.")
        if not deps_ok:
            print("\n📦 Install missing dependencies with:")
            print("   pip install -r requirements.txt")

if __name__ == "__main__":
    main()
