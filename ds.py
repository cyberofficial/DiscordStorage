from discordstorage import core
import threading,json,asyncio,random,sys,argparse,os,time
import urllib.request
import urllib.error
import zipfile
import hashlib
import subprocess
import shutil

TOKEN_SECRET = "" #bot's secret token
ROOM_ID = "" #channel text ID
BOT_INFO = None
FILES = None

# File type detection setup
FILE_UTILITY_PATH = os.path.join(os.getcwd(), "file.exe")
MAGIC_DB_PATH = os.path.join(os.getcwd(), "magic.mgc")
LIBMAGIC_PATH = os.path.join(os.getcwd(), "libmagic.dll")

#Generates a file code from 0-4097
def genCode():
    code = str(random.randint(0,4098))
    if FILES == None:
        return code
    while code in FILES.keys():
        code = str(random.randint(0,4098))
    return code

#returns if the config file is configured or not.
def isConfigured():
    return os.path.isfile('config.discord')

#invokes file uploading, to be used on a thread that's not in main thread.
#writes to config file accordingly.
def tellupload(line1,line2,cmd,code,client):
    while not (client.isready()):
        time.sleep(0.5)
    if not os.path.isfile(cmd):
        print('[ERROR] File does not exist.')
        client.logout()
        return
    flcode = client.upload(cmd,code)
    if flcode == -1:
        print('[ERROR] File upload fail')
    else:
        jobject = json.loads(line2)
        # flcode now includes: [filename, size, urls, hash_url, file_hash]
        jobject[code] = flcode
        f = open('config.discord','w')
        f.write(line1)
        f.write(json.dumps(jobject))
        f.close()
        print('[DONE] File upload complete')
        print(f'[INFO] File hash: {flcode[4]}')
    client.logout()

def GetHumanReadable(size,precision=2):
    suffixes=['B','KB','MB','GB','TB']
    suffixIndex = 0
    while size > 1024 and suffixIndex < 4:
        suffixIndex += 1 #increment the index of the suffix
        size = size/1024.0 #apply the division
    return "%.*f%s"%(precision,size,suffixes[suffixIndex])

#invokes file downloading, to be used on a thread that's not in main thread
def telldownload(client,inp):
    while not (client.isready()):
        time.sleep(0.5)
    client.download(inp)
    client.logout()

# Download and setup file type detection utility
def setup_file_utility():
    """Download and extract Windows file utility if not present"""
    if os.path.exists(FILE_UTILITY_PATH) and os.path.exists(MAGIC_DB_PATH) and os.path.exists(LIBMAGIC_PATH):
        return True
    
    print("📦 Setting up file type detection utility...")
    
    try:
        # Download the file utility
        url = "https://github.com/julian-r/file-windows/releases/download/v5.44/file_5.44-build104-vs2022-x64.zip"
        zip_path = "file_utility.zip"
        
        print("⬇️  Downloading file utility...")
        urllib.request.urlretrieve(url, zip_path)
        
        # Extract the zip file
        print("📂 Extracting file utility...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall()
        
        # Move files to the correct location if needed
        extracted_files = ["file.exe", "magic.mgc", "libmagic.dll"]
        for file_name in extracted_files:
            if os.path.exists(file_name):
                continue
            # Look for the file in subdirectories
            for root, dirs, files in os.walk("."):
                if file_name in files:
                    src = os.path.join(root, file_name)
                    dst = os.path.join(os.getcwd(), file_name)
                    shutil.move(src, dst)
                    break
        
        # Clean up
        os.remove(zip_path)
        
        # Clean up any extracted directories
        for item in os.listdir("."):
            if os.path.isdir(item) and item.startswith("file_"):
                shutil.rmtree(item)
        
        print("✅ File utility setup complete")
        return True
        
    except Exception as e:
        print(f"❌ Failed to setup file utility: {str(e)}")
        return False

def detect_file_type(file_path):
    """Detect file type using the Windows file utility"""
    if not os.path.exists(FILE_UTILITY_PATH):
        if not setup_file_utility():
            return "unknown"
    
    try:
        # Run file.exe to detect file type
        result = subprocess.run([FILE_UTILITY_PATH, "-b", file_path], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            file_type = result.stdout.strip()
            return file_type
        else:
            return "unknown"
            
    except Exception as e:
        print(f"⚠️  File type detection failed: {str(e)}")
        return "unknown"

def guess_file_extension(file_type):
    """Guess file extension based on file type description"""
    file_type_lower = file_type.lower()
    
    # Common file type mappings
    extension_map = {
        'jpeg': '.jpg',
        'jpg': '.jpg',
        'png': '.png',
        'gif': '.gif',
        'webp': '.webp',
        'bmp': '.bmp',
        'bitmap': '.bmp',
        'tiff': '.tiff',
        'svg': '.svg',
        'ico': '.ico',
        'pdf': '.pdf',
        'zip': '.zip',
        'rar': '.rar',
        '7-zip': '.7z',
        'tar': '.tar',
        'gzip': '.gz',
        'bzip2': '.bz2',
        'microsoft word': '.docx',
        'microsoft excel': '.xlsx',
        'microsoft powerpoint': '.pptx',
        'openoffice': '.odt',
        'mp4': '.mp4',
        'avi': '.avi',
        'mkv': '.mkv',
        'mov': '.mov',
        'wmv': '.wmv',
        'flv': '.flv',
        'webm': '.webm',
        'm4v': '.m4v',
        'mp3': '.mp3',
        'wav': '.wav',
        'flac': '.flac',
        'aac': '.aac',
        'ogg': '.ogg',
        'm4a': '.m4a',
        'wma': '.wma',
        'executable': '.exe',
        'pe32': '.exe',
        'pe32+': '.exe',
        'msi': '.msi',
        'dll': '.dll',
        'text': '.txt',
        'ascii': '.txt',
        'utf-8': '.txt',
        'html': '.html',
        'xml': '.xml',
        'json': '.json',
        'csv': '.csv',
        'python': '.py',
        'javascript': '.js',
        'css': '.css',
        'java': '.java',
        'c source': '.c',
        'c++': '.cpp',
        'c#': '.cs',
        'php': '.php',
        'ruby': '.rb',
        'shell': '.sh',
        'batch': '.bat',
        'powershell': '.ps1',
        'sql': '.sql',
        'iso': '.iso',
        'sqlite': '.db',
        'database': '.db',
        'font': '.ttf',
        'truetype': '.ttf',
        'opentype': '.otf',
        'postscript': '.ps',
        'epub': '.epub',
        'mobi': '.mobi',
        'rtf': '.rtf',
        'xps': '.xps',
        'sketch': '.sketch',
        'psd': '.psd',
        'ai': '.ai',
        'eps': '.eps',
        'dxf': '.dxf',
        'dwg': '.dwg',
        'step': '.step',
        'stl': '.stl',
        'obj': '.obj',
        'fbx': '.fbx',
        'blend': '.blend',
        'unity': '.unity',
        'apk': '.apk',
        'ipa': '.ipa',
        'deb': '.deb',
        'rpm': '.rpm',
        'dmg': '.dmg',
        'pkg': '.pkg'
    }
    
    # Try to find a matching extension
    for file_format, ext in extension_map.items():
        if file_format in file_type_lower:
            return ext
    
    return '.unknown'

def print_url_help():
    """Print helpful information about getting fresh Discord URLs"""
    print("\n" + "="*60)
    print("💡 HOW TO GET FRESH DISCORD URLs:")
    print("="*60)
    print("1. Open Discord in your web browser or desktop app")
    print("2. Navigate to the channel where your files are stored")
    print("3. Find the hash file and chunk files")
    print("4. Right-click on each file → 'Copy Link'")
    print("5. Use the fresh URLs with the recovery command")
    print()
    print("📝 RECOVERY COMMAND FORMAT:")
    print("   python ds.py -r <file_id> <hash_url> <chunk_url1> [chunk_url2] ...")
    print()
    print("💡 TIPS:")
    print("   • Discord CDN URLs expire after some time")
    print("   • Always copy the complete URL (don't truncate)")
    print("   • Hash file should end with .hash")
    print("   • Chunk files should end with .0, .1, .2, etc.")
    print("   • Make sure you have all chunk files")
    print("="*60)

def calculate_file_hash(file_path):
    """Calculate MD5 hash of a file"""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()

def download_url_to_file(url, output_path):
    """Download a file from a URL with better error handling"""
    try:
        print(f"⬇️  Downloading from URL...")
        
        # Add headers that might help with Discord CDN
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        req.add_header('Accept', '*/*')
        req.add_header('Accept-Language', 'en-US,en;q=0.9')
        req.add_header('Accept-Encoding', 'gzip, deflate, br')
        req.add_header('Connection', 'keep-alive')
        req.add_header('Upgrade-Insecure-Requests', '1')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(output_path, 'wb') as f:
                shutil.copyfileobj(response, f)
        
        file_size = os.path.getsize(output_path)
        print(f"✅ Downloaded {file_size} bytes")
        return True
        
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"❌ Download failed: Access forbidden (403)")
            print(f"⚠️  The Discord CDN link has likely expired!")
            print(f"💡 Discord CDN links expire after a certain time period.")
            print(f"📋 You may need to get fresh URLs from Discord.")
        elif e.code == 404:
            print(f"❌ Download failed: File not found (404)")
        else:
            print(f"❌ Download failed: HTTP Error {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"❌ Download failed: Network error - {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Download failed: {str(e)}")
        return False

def recover_files(file_id, hash_url, *chunk_urls):
    """Recover files from URLs and add to config file"""
    print(f"🔄 Starting file recovery for ID: {file_id}")
    print(f"📊 Hash URL: {hash_url}")
    print(f"📦 Chunk URLs: {len(chunk_urls)} chunks")
    print("-" * 50)
    
    # Create recovery directory
    recovery_dir = os.path.join(os.getcwd(), "recovery")
    os.makedirs(recovery_dir, exist_ok=True)
    
    # Download hash file
    hash_file_path = os.path.join(recovery_dir, f"{file_id}.hash")
    print("📥 Downloading hash file...")
    if not download_url_to_file(hash_url, hash_file_path):
        print("❌ Failed to download hash file")
        print_url_help()
        return False
    
    # Read expected hash
    try:
        with open(hash_file_path, 'r') as f:
            expected_hash = f.read().strip()
        print(f"✅ Expected hash: {expected_hash}")
    except Exception as e:
        print(f"❌ Failed to read hash file: {str(e)}")
        return False
    
    # Download all chunks
    chunk_files = []
    failed_chunks = []
    
    for i, chunk_url in enumerate(chunk_urls):
        chunk_path = os.path.join(recovery_dir, f"{file_id}.{i}")
        print(f"📥 Downloading chunk {i+1}/{len(chunk_urls)}...")
        if download_url_to_file(chunk_url, chunk_path):
            chunk_files.append(chunk_path)
            print(f"✅ Chunk {i+1} downloaded successfully")
        else:
            failed_chunks.append(i+1)
            print(f"❌ Failed to download chunk {i+1}")
    
    if failed_chunks:
        print(f"\n❌ Failed to download {len(failed_chunks)} chunk(s): {', '.join(map(str, failed_chunks))}")
        print("💡 Cannot proceed with file recovery - all chunks are required")
        return False
    
    # Combine chunks into single file
    recovered_file_path = os.path.join(recovery_dir, f"{file_id}.unknown")
    print("🔧 Combining chunks...")
    try:
        with open(recovered_file_path, 'wb') as output_file:
            for chunk_file in chunk_files:
                with open(chunk_file, 'rb') as input_file:
                    shutil.copyfileobj(input_file, output_file)
        
        file_size = os.path.getsize(recovered_file_path)
        print(f"✅ Chunks combined successfully ({file_size} bytes)")
    except Exception as e:
        print(f"❌ Failed to combine chunks: {str(e)}")
        return False
    
    # Verify hash
    print("🔍 Verifying file hash...")
    actual_hash = calculate_file_hash(recovered_file_path)
    if actual_hash == expected_hash:
        print(f"✅ Hash verification successful: {actual_hash}")
    else:
        print(f"❌ Hash verification failed!")
        print(f"   Expected: {expected_hash}")
        print(f"   Actual:   {actual_hash}")
        print("⚠️  File may be corrupted!")
        
        # Ask user if they want to continue anyway
        response = input("❓ Continue with corrupted file? (y/n): ").lower().strip()
        if response not in ['y', 'yes']:
            print("🛑 Recovery aborted by user")
            return False
        else:
            print("⚠️  Continuing with potentially corrupted file...")
    
    # Detect file type
    print("🔎 Scanning file type...")
    file_type = detect_file_type(recovered_file_path)
    print(f"📋 Detected file type: {file_type}")
    
    # Guess extension
    guessed_ext = guess_file_extension(file_type)
    print(f"💡 Suggested extension: {guessed_ext}")
    
    # Ask user if they want to rename the file
    if guessed_ext != '.unknown':
        response = input(f"🤔 We think the file type is \"{guessed_ext[1:].upper()}\" - rename it? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            new_name = f"{file_id}{guessed_ext}"
            new_path = os.path.join(recovery_dir, new_name)
            try:
                os.rename(recovered_file_path, new_path)
                recovered_file_path = new_path
                print(f"✅ File renamed to: {new_name}")
            except Exception as e:
                print(f"⚠️  Failed to rename file: {str(e)}")
    else:
        print("🤷 Could not determine file type - keeping as .unknown")
        
        # Ask user if they want to specify an extension manually
        response = input("❓ Would you like to specify a file extension manually? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            manual_ext = input("📝 Enter file extension (e.g., .txt, .jpg, .exe): ").strip()
            if manual_ext and not manual_ext.startswith('.'):
                manual_ext = '.' + manual_ext
            
            if manual_ext and len(manual_ext) > 1:
                new_name = f"{file_id}{manual_ext}"
                new_path = os.path.join(recovery_dir, new_name)
                try:
                    os.rename(recovered_file_path, new_path)
                    recovered_file_path = new_path
                    print(f"✅ File renamed to: {new_name}")
                except Exception as e:
                    print(f"⚠️  Failed to rename file: {str(e)}")
    
    # Clean up temporary files
    try:
        os.remove(hash_file_path)
        for chunk_file in chunk_files:
            os.remove(chunk_file)
        print("🧹 Cleaned up temporary files")
    except Exception as e:
        print(f"⚠️  Could not clean up some temporary files: {str(e)}")
      # Move to downloads folder
    downloads_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    final_path = os.path.join(downloads_dir, os.path.basename(recovered_file_path))
    
    try:
        shutil.move(recovered_file_path, final_path)
        print(f"📁 File recovered and saved to: downloads/{os.path.basename(final_path)}")
        
        # Add recovered file to config.discord if it exists
        if isConfigured():
            try:                # Read current config
                with open('config.discord', 'r') as f:
                    first_line = f.readline()
                    second_line = f.readline()
                
                # Ensure we have both lines
                if not first_line.strip():
                    raise Exception("Invalid config file - missing bot configuration")
                
                if not second_line.strip():
                    second_line = "{}"  # Empty files database
                  # Parse the files data
                files_data = json.loads(second_line) if second_line.strip() else {}
                
                # Check if file_id already exists
                if file_id in files_data:
                    print(f"⚠️  File ID {file_id} already exists in config database")
                    response = input(f"   Overwrite existing entry? (y/n): ").lower().strip()
                    if response not in ['y', 'yes']:
                        print("   File recovered but not added to database to avoid overwriting existing entry")
                        print("🎉 Recovery completed successfully!")
                        return True
                
                # Get file stats
                file_size = os.path.getsize(final_path)
                filename = os.path.basename(final_path)
                
                # Create file record in the same format as uploads
                # [filename, size, urls, hash_url, file_hash]
                file_record = [
                    filename,
                    file_size,
                    list(chunk_urls),  # Convert tuple to list for JSON serialization
                    hash_url,
                    expected_hash
                ]
                
                # Add to files data with the provided file_id
                files_data[file_id] = file_record
                
                # Write updated config back
                with open('config.discord', 'w') as f:
                    f.write(first_line)
                    f.write(json.dumps(files_data))
                
                print(f"💾 File added to config database with ID: {file_id}")
                print(f"📋 You can now use: python ds.py -d {file_id} to re-download this file")
                
            except Exception as e:
                print(f"⚠️  Could not add file to config database: {str(e)}")
                print("   File recovery was successful, but file won't appear in -list")
        else:
            print("💡 No config.discord file found - file recovered but not added to database")
            print("   Create a config file to manage recovered files with ds.py commands")
        
        print("🎉 Recovery completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to move file to downloads: {str(e)}")
        print(f"📁 File is available at: {recovered_file_path}")
        return True  # Still consider it successful

def parseArgs(inp):
    commands = ['-h','-help','-l','-list','-d','-download','-u','-upload','-r','-recover']
    if(len(inp) == 1):
        print('----------------------\n|DiscordStorage v0.1 |')
        print('|github.com/nigelchen|\n----------------------')
        print('\nUsage: python ds.py [command] (target)\n')
        print('COMMANDS:')
        print('[-h, -help] :: Show the current message')
        print('[-l, -list] :: Lists all the file informations that has been uploaded to the server.')
        print('[-d, -download] (FILE CODE) :: Downloads a file from the server. A filecode is taken in as the file identifier.')
        print('[-u, -upload] (FILE DIRECTORY) :: Uploads a file to the server. The full file directory is taken in for the argument.')
        print('[-r, -recover] (FILE ID) (HASH URL) (CHUNK URLs...) :: Recover a lost file from Discord URLs.\n')
    elif isConfigured():
        f = open('config.discord','r')
        first = f.readline()
        second = f.readline()
        f.close()
        TOKEN_SECRET = json.loads(first.replace("\\n",""))['TOKEN']
        for el in inp:
            if '-d' == el or '-download' == el:
                if not ((not(FILES == None)) and (inp[inp.index(el)+1] in FILES.keys())):
                    print('\n[ERROR] File code not found\n')
                else:
                    obj = json.loads(second)[inp[inp.index(el)+1]]
                    print('DOWNLOADING: ' + obj[0] )
                    print('SIZE: ' + GetHumanReadable(obj[1]))
                    client = core.Core(os.getcwd() + "/",TOKEN_SECRET,ROOM_ID)
                    threading.Thread(target=telldownload,args=(client,obj,)).start()
                    client.start()
                    break
            elif '-u' == el or '-upload' == el:
                print('UPLOADING: ' + inp[inp.index(el)+1])
                client = core.Core(os.getcwd() + "/",TOKEN_SECRET,ROOM_ID)
                threading.Thread(target=tellupload,args=(first,second,inp[inp.index(el)+1],genCode(),client,)).start()
                client.start()
                break
            elif '-list' == el or '-l' == el:
                if not (FILES == None):
                    print('\nFILES UPLOADED TO DISCORD:\n')
                    for key in FILES.keys():
                        if FILES[key] == None:   
                            #correct nullfied attribute
                            print(' [CONSOLE] Removed incorrect file with filecode ' + str(key))
                            f = open('config.discord','w')
                            f.write(first)
                            jobject = json.loads(second)
                            del jobject[key]
                            f.write(json.dumps(jobject))
                            f.close()
                        else:
                            # Handle both old format [name, size, urls] and new format [name, size, urls, hash_url, hash]
                            file_info = FILES[key]
                            name = str(file_info[0])
                            size = GetHumanReadable(file_info[1])
                            hash_info = ""
                            if len(file_info) >= 5:  # New format with hash
                                hash_info = f" | hash: {file_info[4][:8]}..."
                            print(f'name: {name} | code: {str(key)} | size: {size}{hash_info}')
                    print('\n')
                    break
            elif '-help' == el or '-h' == el:
                print('----------------------\n|DiscordStorage|')
                print('|github.com/nigel|\n----------------------')
                print('\nUsage: python ds.py [command] (target)\n')
                print('COMMANDS:')
                print('[-h, -help] :: Show the current message')
                print('[-l, -list] :: Lists all the file informations that has been uploaded to the server.')
                print('[-d, -download] (FILE CODE) :: Downloads a file from the server. A filecode is taken in as the file identifier.')
                print('[-u, -upload] (FILE DIRECTORY) :: Uploads a file to the server. The full file directory is taken in for the argument.')
                print('[-r, -recover] (FILE ID) (HASH URL) (CHUNK URLs...) :: Recover a lost file from Discord URLs.\n')
            elif '-r' == el or '-recover' == el:
                # Handle recovery command: ds.py -r <id> <hash_url> <chunk1> <chunk2> ...
                try:
                    recovery_index = inp.index(el)
                    if len(inp) < recovery_index + 4:  # Need at least: -r, id, hash_url, and one chunk
                        print('\n[ERROR] Recovery command requires: file_id, hash_url, and at least one chunk URL\n')
                        print('Usage: python ds.py -r <file_id> <hash_url> <chunk_url1> [chunk_url2] ...\n')
                        break
                    
                    file_id = inp[recovery_index + 1]
                    hash_url = inp[recovery_index + 2]
                    chunk_urls = inp[recovery_index + 3:]  # All remaining arguments are chunk URLs
                    
                    # Validate inputs
                    if not file_id.isdigit():
                        print(f'\n[ERROR] File ID must be numeric, got: {file_id}\n')
                        break
                    
                    if not hash_url.startswith('http'):
                        print(f'\n[ERROR] Hash URL must be a valid HTTP URL\n')
                        break
                    
                    # Check if file ID already exists
                    if FILES is not None and file_id in FILES:
                        print(f'\n⚠️  Warning: File ID {file_id} already exists in your database')
                        print(f'   Current file: {FILES[file_id][0]}')
                        response = input('   Continue with recovery anyway? This will overwrite the existing entry (y/n): ').lower().strip()
                        if response not in ['y', 'yes']:
                            print('   Recovery cancelled by user')
                            break
                    
                    for i, chunk_url in enumerate(chunk_urls):
                        if not chunk_url.startswith('http'):
                            print(f'\n[ERROR] Chunk URL {i+1} must be a valid HTTP URL\n')
                            break
                    else:
                        # All URLs are valid, proceed with recovery
                        print(f'\n🔄 Starting file recovery...')
                        if recover_files(file_id, hash_url, *chunk_urls):
                            print('\n✅ File recovery completed successfully!')
                        else:
                            print('\n❌ File recovery failed!')
                        break
                    
                except ValueError:
                    print('\n[ERROR] Recovery command not found in arguments\n')
                except Exception as e:
                    print(f'\n[ERROR] Recovery failed: {str(e)}\n')
                break

if not isConfigured():
    # Check if this is a recovery command first (doesn't need config)
    if len(sys.argv) > 1 and (sys.argv[1] == '-r' or sys.argv[1] == '-recover'):
        try:
            if len(sys.argv) < 5:  # Need at least: script, -r, id, hash_url, and one chunk
                print('\n[ERROR] Recovery command requires: file_id, hash_url, and at least one chunk URL\n')
                print('Usage: python ds.py -r <file_id> <hash_url> <chunk_url1> [chunk_url2] ...\n')
            else:
                file_id = sys.argv[2]
                hash_url = sys.argv[3]
                chunk_urls = sys.argv[4:]  # All remaining arguments are chunk URLs
                
                # Validate inputs
                if not file_id.isdigit():
                    print(f'\n[ERROR] File ID must be numeric, got: {file_id}\n')
                elif not hash_url.startswith('http'):
                    print(f'\n[ERROR] Hash URL must be a valid HTTP URL\n')
                else:
                    # Validate chunk URLs
                    valid_chunks = True
                    for i, chunk_url in enumerate(chunk_urls):
                        if not chunk_url.startswith('http'):
                            print(f'\n[ERROR] Chunk URL {i+1} must be a valid HTTP URL\n')
                            valid_chunks = False
                            break
                    
                    if valid_chunks:
                        # All URLs are valid, proceed with recovery
                        print(f'\n🔄 Starting file recovery...')
                        if recover_files(file_id, hash_url, *chunk_urls):
                            print('\n✅ File recovery completed successfully!')
                        else:
                            print('\n❌ File recovery failed!')
                        
        except Exception as e:
            print(f'\n[ERROR] Recovery failed: {str(e)}\n')
    else:
        print('Welcome to DiscordStorage.')
        print('Go to http://github.com/nigelchen/DiscordStorage for instructions.')
        TOKEN_SECRET = input('Bot token ID (Will be stored in plaintext in config file):')
        ROOM_ID = input ('Enter channel ID to store files in:')
        if len(ROOM_ID) <=0:
            ROOM_ID = None
        f = open('config.discord','w')
        f.write(str(json.dumps({'TOKEN':TOKEN_SECRET,'ROOM_ID':ROOM_ID})) + "\n")
        f.write(str(json.dumps({})))
        f.close()
else:
    f = open('config.discord','r')
    first = f.readline()
    second = f.readline()
    BOT_INFO = json.loads(first)
    FILES = json.loads(second)
    TOKEN_SECRET = json.loads(first.replace("\\n",""))['TOKEN']
    ROOM_ID = json.loads(first.replace("\\n",""))['ROOM_ID']
    f.close()

try:
    parseArgs(sys.argv)
except IndexError:
    print('\nUsage: python ds.py [command] (target)\n')
    print('COMMANDS:')
    print('[-h, -help] :: Show the help message')
    print('[-l, -list] :: Lists all the file informations that has been uploaded to the server.')
    print('[-d, -download] (FILE CODE) :: Downloads a file from the server. A filecode is taken in as the file identifier.')
    print('[-u, -upload] (FILE DIRECTORY) :: Uploads a file to the server. The full file directory is taken in for the argument.')
    print('[-r, -recover] (FILE ID) (HASH URL) (CHUNK URLs...) :: Recover a lost file from Discord URLs.\n')
