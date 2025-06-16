import os,io,aiohttp,asyncio, discord, time
from typing import cast
from .Session import Session

class Core:

    def __init__(self,directory,token,channel):
        self.directory = directory #set root directory for downloaded/files to be uploaded
        self.session = Session(token,channel) #discord API
        self.client = self.session.getClient() #discord API client object

    #check if the client is connected to discord servers
    def isready(self):
        return not(self.session.getLoop() == None)    #starts conenction to discord servers. 
    #RUNS ON MAIN THREAD, ASYNC.
    def start(self):
        self.session.start()

    #Halts all connection to discord servers.
    def logout(self):
         loop = self.session.getLoop()
         if loop is not None:
             future = asyncio.run_coroutine_threadsafe(self.session.logout(), loop)
    
    #runs the async_upload in a threadsafe way,
    #can be run from anything outisde of main thread.
    def upload(self,inp,code):
         loop = self.session.getLoop()
         if loop is None:
             print('[ERROR] Discord session not ready')
             return -1
         future = asyncio.run_coroutine_threadsafe(self.async_upload(inp,code), loop)
         try:
            return future.result()
         except Exception as exc:
            print(exc)
            return -1
       #runs the async_download in a threadsafe way,
    #can be run from an ything outside of main thread.
    def download(self,inp):
        loop = self.session.getLoop()
        if loop is None:
            print('[ERROR] Discord session not ready')
            return -1
        future = asyncio.run_coroutine_threadsafe(self.async_download(inp), loop)
        try:
            return future.result()
        except Exception as exc:
            print('[ERROR] ' + str(exc))
            return -1    #Downloads a file from the server.
    #The list object in this format is needed: [filename,size,[DL URLs],hash_url,original_hash]
    #RUNS ON MAIN THREAD, ASYNC.
    async def async_download(self,inp):
            filename = inp[0]
            total_size = inp[1]
            urls = inp[2]
            hash_url = inp[3] if len(inp) > 3 else None
            original_hash = inp[4] if len(inp) > 4 else None
            total_chunks = len(urls)
            
            print(f"\n📥 Starting download: {filename}")
            print(f"📊 File size: {self.GetHumanReadable(total_size)}")
            print(f"🔢 Total chunks: {total_chunks}")
            print("-" * 50)
            
            # Create download directory and progress tracking
            import hashlib
            file_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
            download_dir = os.path.join(self.directory, "downloading", f"{filename}_{file_hash}")
            progress_file = os.path.join(download_dir, "progress.json")
            output_file = os.path.join(self.directory, "downloads", filename)
            
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            os.makedirs(download_dir, exist_ok=True)
            
            # Download hash file first if available
            downloaded_hash = None
            if hash_url:
                print("📥 Downloading hash file first...")
                try:
                    agent = {'User-Agent':'DiscordStorageBot (http://github.com/nigel/discordstorage)'}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(hash_url, headers=agent) as r:
                            if r.status == 200:
                                hash_content = await r.read()
                                downloaded_hash = hash_content.decode('utf-8').strip()
                                print(f"✅ Expected file hash: {downloaded_hash}")
                            else:
                                print(f"⚠️  Failed to download hash file (HTTP {r.status})")
                except Exception as e:
                    print(f"⚠️  Failed to download hash file: {str(e)}")
            elif original_hash:
                downloaded_hash = original_hash
                print(f"✅ Using stored hash: {downloaded_hash}")
            else:
                print("⚠️  No hash information available for verification")
            
            # Check if we're resuming a download
            resume_data = self.load_resume_data(progress_file)
            if resume_data and resume_data.get('completed_chunks'):
                completed_chunks = set(resume_data['completed_chunks'])
                print(f"🔄 Found previous download progress: {len(completed_chunks)}/{total_chunks} chunks completed")
                print(f"📋 Resuming download...")
            else:
                completed_chunks = set()
                print("📋 Starting fresh download...")
            
            start_time = time.time()
            downloaded_bytes = len(completed_chunks) * 9000000  # Approximate chunk size
            
            # Create/open the output file
            f = open(output_file, 'r+b' if completed_chunks else 'wb')
            
            for i in range(total_chunks):
                    # Skip already completed chunks
                    if i in completed_chunks:
                        print(f"⏭️  Chunk {i+1}/{total_chunks} already downloaded, skipping...")
                        continue
                        
                    chunk_start_time = time.time()
                    chunk_size = 0
                    
                    # Retry mechanism with exponential backoff
                    retry_count = 0
                    retry_delays = [1, 5, 15, 30]  # 1s, 5s, 15s, then 30s forever
                    download_successful = False
                    
                    while not download_successful:
                        try:
                            if retry_count == 0:
                                print(f"⬇️  Downloading chunk {i+1}/{total_chunks}...", end=" ")
                            else:
                                print(f"🔄 Retry {retry_count} for chunk {i+1}/{total_chunks}...", end=" ")
                            
                            #user agent is not in compliance with Discord API rules. Change accordingly if needed
                            agent = {'User-Agent':'DiscordStorageBot (http://github.com/nigel/discordstorage)'}
                            
                            # Download chunk to temporary location first
                            chunk_data = bytearray()
                            async with aiohttp.ClientSession() as session:
                                async with session.get(urls[i], headers=agent) as r:
                                        if r.status == 200:
                                                async for data in r.content.iter_any():
                                                        chunk_data.extend(data)
                                                        chunk_size += len(data)
                                        else:
                                            raise Exception(f"HTTP {r.status}")
                            
                            # Write chunk to correct position in file
                            f.seek(i * 9000000)  # Seek to chunk position
                            f.write(chunk_data)
                            f.flush()  # Ensure data is written
                            
                            downloaded_bytes += chunk_size
                            completed_chunks.add(i)
                            download_successful = True
                            
                        except Exception as e:
                            retry_count += 1
                            
                            # Determine retry delay (1s, 5s, 15s, then stay at 30s)
                            if retry_count <= len(retry_delays):
                                delay = retry_delays[retry_count - 1]
                            else:
                                delay = retry_delays[-1]  # Stay at 30s
                            
                            print(f"❌ Failed: {str(e)}")
                            print(f"⏱️  Waiting {delay}s before retry {retry_count}... (Press Ctrl+C to abort)")
                            
                            try:
                                await asyncio.sleep(delay)
                            except KeyboardInterrupt:
                                f.close()
                                print("\n❌ Download cancelled by user")
                                # Save progress before exiting
                                self.save_resume_data(progress_file, {
                                    'completed_chunks': list(completed_chunks),
                                    'total_chunks': total_chunks,
                                    'file_size': total_size,
                                    'filename': filename
                                })
                                raise Exception("Download cancelled by user")
                    
                    # Calculate and display progress (only after successful download)
                    chunk_time = time.time() - chunk_start_time
                    total_time = time.time() - start_time
                    
                    # Calculate speeds
                    chunk_speed = chunk_size / chunk_time if chunk_time > 0 else 0
                    avg_speed = downloaded_bytes / total_time if total_time > 0 else 0
                    
                    # Calculate progress percentage  
                    progress = (len(completed_chunks) / total_chunks) * 100
                    
                    # Display progress
                    print(f"✅ ({self.GetHumanReadable(chunk_size)}) ({chunk_speed * 8 / 1024 / 1024:.1f} Mbps)")
                    print(f"📈 Progress: {progress:.1f}% | Avg Speed: {avg_speed * 8 / 1024 / 1024:.1f} Mbps | ETA: {self.calculate_eta((total_chunks - len(completed_chunks)) * 9000000, avg_speed)}")
                    
                    if i < total_chunks - 1:  # Don't print separator after last chunk
                        print("   " + "█" * int(progress/2) + "░" * int(50-progress/2) + f" {len(completed_chunks)}/{total_chunks} chunks")
                    
                    # Save progress after each successful chunk
                    self.save_resume_data(progress_file, {
                        'completed_chunks': list(completed_chunks),
                        'total_chunks': total_chunks,
                        'file_size': total_size,
                        'filename': filename
                    })
            
            f.close()
            
            total_time = time.time() - start_time
            avg_speed = total_size / total_time if total_time > 0 else 0
            
            print("-" * 50)
            print(f"🎉 Download completed!")
            print(f"⏱️  Total time: {total_time:.1f}s")
            print(f"🚀 Average speed: {avg_speed * 8 / 1024 / 1024:.1f} Mbps")
            print(f"📁 Saved to: downloads/{filename}")
              # --- Verify file hash after download ---
            print(f"🔎 Verifying file hash after download...")
            import hashlib
            md5 = hashlib.md5()
            with open(output_file, "rb") as f_hash:
                for chunk in iter(lambda: f_hash.read(8192), b""):
                    md5.update(chunk)
            actual_hash = md5.hexdigest()
            
            if downloaded_hash:
                if actual_hash == downloaded_hash:
                    print(f"✅ File hash verification successful: {actual_hash}")
                else:
                    print(f"❌ [ERROR] File hash mismatch!")
                    print(f"   Expected: {downloaded_hash}")
                    print(f"   Actual:   {actual_hash}")
                    print(f"⚠️  File may be corrupted or incomplete!")
            else:
                print(f"⚠️  No hash available for verification. Calculated hash: {actual_hash}")
            # --- End hash verification ---
              # Clean up temporary files
            self.cleanup_upload_dir(download_dir)
            #files[code] = [name,size,[urls]]    #Uploads a file to the server from the root directory, or any other directory specified
    #inp = directory, code = application-generated file code    #RUNS ON MAIN THREAD, ASYNC.
    async def async_upload(self,inp,code):
            urls = []
            hash_url = None
            # --- Calculate and save file hash before upload ---
            import hashlib
            hash_path = inp + ".hash"
            print(f"🔎 Calculating file hash before upload...")
            md5 = hashlib.md5()
            with open(inp, "rb") as f_hash:
                for chunk in iter(lambda: f_hash.read(8192), b""):
                    md5.update(chunk)
            file_md5 = md5.hexdigest()
            with open(hash_path, "w") as f_hash_out:
                f_hash_out.write(file_md5)
            print(f"✅ File hash: {file_md5} (saved to {hash_path})")
            # --- End hash calculation ---
            channel = self.session.getChannel()
            
            # Check if channel exists and is a messageable channel
            if channel is None:
                raise Exception("Channel not found - check your channel ID configuration")
            
            # Check if it's a text channel or DM channel that supports messaging
            if not isinstance(channel, (discord.TextChannel, discord.DMChannel, discord.GroupChannel)):
                raise Exception("Channel must be a text channel, DM, or group channel for file uploads")
            
            # Calculate file info for progress tracking
            file_size = os.path.getsize(inp)
            total_chunks = self.splitFile(inp)
            chunk_size = 9000000  # 9MB
            
            print(f"\n📤 Starting upload: {os.path.basename(inp)}")
            print(f"📊 File size: {self.GetHumanReadable(file_size)}")
            print(f"🔢 Total chunks: {total_chunks}")
            print(f"📦 Chunk size: {self.GetHumanReadable(chunk_size)}")
            print("-" * 50)
            
            # Create uploading directory and pre-chunk the file
            # Use file path hash for consistent resume identification
            import hashlib
            file_hash = hashlib.md5(inp.encode()).hexdigest()[:8]
            upload_dir = os.path.join(self.directory, "uploading", f"{os.path.basename(inp)}_{file_hash}")
            progress_file = os.path.join(upload_dir, "progress.json")
              # Check if we're resuming an upload
            resume_data = self.load_resume_data(progress_file)
            if resume_data:
                print(f"🔄 Found previous upload progress: {resume_data['last_completed_chunk'] + 1}/{total_chunks} chunks completed")
                print(f"📋 Resuming from chunk {resume_data['last_completed_chunk'] + 1}")
                urls = resume_data['urls']
                hash_url = resume_data.get('hash_url')
                start_chunk = resume_data['last_completed_chunk'] + 1
                # Use the existing upload code for consistency
                if 'upload_code' in resume_data:
                    code = resume_data['upload_code']
                    print(f"📋 Using existing upload code: {code}")
            else:
                print("📋 Pre-chunking file for reliable upload...")
                self.pre_chunk_file(inp, upload_dir, chunk_size, total_chunks)
                start_chunk = 0

            # Upload hash file first if not already uploaded
            if not hash_url:
                print("📤 Uploading hash file...")
                try:
                    with open(hash_path, 'rb') as hash_file:
                        hash_content = hash_file.read()
                    
                    o = io.BytesIO(hash_content)
                    discord_file = discord.File(fp=o, filename=code + ".hash")
                    await channel.send(file=discord_file)
                      # Get the uploaded hash file URL
                    async for message in channel.history(limit=1):
                        if message.author == self.client.user:
                            hash_url = message.attachments[0].url
                            break
                    
                    print(f"✅ Hash file uploaded successfully")
                    
                    # Clean up local hash file after successful upload
                    try:
                        os.remove(hash_path)
                        print(f"🧹 Cleaned up local hash file")
                    except Exception as cleanup_error:
                        print(f"⚠️  Could not clean up hash file: {str(cleanup_error)}")
                        
                except Exception as e:
                    print(f"❌ Failed to upload hash file: {str(e)}")
                    raise Exception("Hash file upload failed")
            
            start_time = time.time()
            uploaded_bytes = start_chunk * chunk_size
            
            for i in range(start_chunk, total_chunks):
                    chunk_start_time = time.time()
                    
                    # Read chunk data from pre-chunked file
                    chunk_path = os.path.join(upload_dir, f"chunk_{i:03d}.bin")
                    with open(chunk_path, 'rb') as chunk_file:
                        chunk_data = chunk_file.read()
                    actual_chunk_size = len(chunk_data)
                    
                    # Retry mechanism with exponential backoff
                    retry_count = 0
                    max_retries = None  # Unlimited retries
                    retry_delays = [1, 5, 15, 30]  # 1s, 5s, 15s, then 30s forever
                    upload_successful = False
                    
                    while not upload_successful:
                        try:
                            o = io.BytesIO(chunk_data)
                            discord_file = discord.File(fp=o,filename=code+"." + str(i))
                            
                            if retry_count == 0:
                                print(f"⬆️  Uploading chunk {i+1}/{total_chunks} ({self.GetHumanReadable(actual_chunk_size)})...", end=" ")
                            else:
                                print(f"🔄 Retry {retry_count} for chunk {i+1}/{total_chunks}...", end=" ")
                            
                            await channel.send(file=discord_file)                            
                            # Get the uploaded file URL
                            async for message in channel.history(limit=None):
                                    if message.author == self.client.user:
                                            urls.append(message.attachments[0].url)
                                            break
                            
                            upload_successful = True
                            # Success indicator will be shown in progress display
                            
                        except Exception as e:
                            retry_count += 1
                              # Determine retry delay (1s, 5s, 15s, then stay at 30s)
                            if retry_count <= len(retry_delays):
                                delay = retry_delays[retry_count - 1]
                            else:
                                delay = retry_delays[-1]  # Stay at 30s
                            
                            print(f"❌ Failed: {str(e)}")
                            print(f"⏱️  Waiting {delay}s before retry {retry_count}... (Press Ctrl+C to abort)")
                            
                            try:
                                await asyncio.sleep(delay)
                            except KeyboardInterrupt:
                                print("\n❌ Upload cancelled by user")                                # Save progress before exiting
                                self.save_resume_data(progress_file, {
                                    'urls': urls,
                                    'hash_url': hash_url,
                                    'last_completed_chunk': i - 1,
                                    'file_size': file_size,
                                    'total_chunks': total_chunks,
                                    'upload_code': code
                                })
                                raise Exception("Upload cancelled by user")
                    
                    # Calculate and display progress (only after successful upload)
                    uploaded_bytes += actual_chunk_size
                    chunk_time = time.time() - chunk_start_time
                    total_time = time.time() - start_time
                    
                    # Calculate speeds
                    chunk_speed = actual_chunk_size / chunk_time if chunk_time > 0 else 0
                    avg_speed = uploaded_bytes / total_time if total_time > 0 else 0
                    
                    # Calculate progress percentage
                    progress = (uploaded_bytes / file_size) * 100
                      # Display progress
                    print(f"✅ ({chunk_speed * 8 / 1024 / 1024:.1f} Mbps)")
                    print(f"📈 Progress: {progress:.1f}% | Avg Speed: {avg_speed * 8 / 1024 / 1024:.1f} Mbps | ETA: {self.calculate_eta(file_size - uploaded_bytes, avg_speed)}")
                    
                    if i < total_chunks - 1:  # Don't print separator after last chunk
                        print("   " + "█" * int(progress/2) + "░" * int(50-progress/2) + f" {uploaded_bytes}/{file_size} bytes")
                      # Save progress after each successful chunk
                    self.save_resume_data(progress_file, {
                        'urls': urls,
                        'hash_url': hash_url,
                        'last_completed_chunk': i,
                        'file_size': file_size,
                        'total_chunks': total_chunks,
                        'upload_code': code
                    })
            
            # Upload completed successfully
            total_time = time.time() - start_time
            avg_speed = file_size / total_time if total_time > 0 else 0
            
            print("-" * 50)
            print(f"🎉 Upload completed!")
            print(f"⏱️  Total time: {total_time:.1f}s")
            print(f"🚀 Average speed: {avg_speed * 8 / 1024 / 1024:.1f} Mbps")
            print(f"📋 File code: {code}")
              # Clean up temporary files
            self.cleanup_upload_dir(upload_dir)

            return [os.path.basename(inp),os.path.getsize(inp),urls,hash_url,file_md5]

    #Finds out how many file blocks are needed to upload a file.
    #Regular max upload size at a time: 8MB.
    #Discord NITRO max upload size at a time: 50MB.
    #Currently configured for 9MB chunks.
    #Change accordingly if needed.
    def splitFile(self,f):
            if (os.path.getsize(f)/9000000) > 1:
                    return int(os.path.getsize(f)/9000000) + 1
            else:
                    return 1

    # Helper method to convert bytes to human readable format
    def GetHumanReadable(self, size, precision=2):
        suffixes=['B','KB','MB','GB','TB']
        suffixIndex = 0
        while size > 1024 and suffixIndex < 4:
            suffixIndex += 1
            size = size/1024.0
        return "%.*f%s"%(precision,size,suffixes[suffixIndex])
    
    # Helper method to calculate estimated time of arrival
    def calculate_eta(self, remaining_bytes, speed):
        if speed <= 0:
            return "Unknown"
        eta_seconds = remaining_bytes / speed
        if eta_seconds < 60:
            return f"{eta_seconds:.0f}s"
        elif eta_seconds < 3600:
            return f"{eta_seconds/60:.0f}m {eta_seconds%60:.0f}s"
        else:
            hours = eta_seconds // 3600
            minutes = (eta_seconds % 3600) // 60
            return f"{hours:.0f}h {minutes:.0f}m"
    
    # Pre-chunk the file into smaller pieces for resume capability
    def pre_chunk_file(self, file_path, upload_dir, chunk_size, total_chunks):
        os.makedirs(upload_dir, exist_ok=True)
        
        print("📋 Creating chunks...", end=" ")
        with open(file_path, 'rb') as f:
            for i in range(total_chunks):
                chunk_path = os.path.join(upload_dir, f"chunk_{i:03d}.bin")
                if not os.path.exists(chunk_path):  # Skip if chunk already exists
                    chunk_data = f.read(chunk_size)
                    with open(chunk_path, 'wb') as chunk_file:
                        chunk_file.write(chunk_data)
                
                # Show progress
                if (i + 1) % 5 == 0 or i == total_chunks - 1:
                    print(f"({i + 1}/{total_chunks})", end=" ")
        
        print("✅ Chunks created!")
    
    # Load resume data from progress file
    def load_resume_data(self, progress_file):
        if not os.path.exists(progress_file):
            return None
        
        try:
            import json
            with open(progress_file, 'r') as f:
                return json.load(f)
        except:
            return None
    
    # Save resume data to progress file
    def save_resume_data(self, progress_file, data):
        try:
            import json
            os.makedirs(os.path.dirname(progress_file), exist_ok=True)
            with open(progress_file, 'w') as f:
                json.dump(data, f)
        except:
            pass  # Don't fail upload if we can't save progress
    
    # Clean up upload directory after successful upload
    def cleanup_upload_dir(self, upload_dir):
        try:
            import shutil
            if os.path.exists(upload_dir):
                shutil.rmtree(upload_dir)
                print("🧹 Cleaned up temporary files")
        except:
            print("⚠️  Could not clean up temporary files (not critical)")
