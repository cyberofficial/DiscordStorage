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
            return -1

    #Downloads a file from the server.
    #The list object in this format is needed: [filename,size,[DL URLs]]
    #RUNS ON MAIN THREAD, ASYNC.
    async def async_download(self,inp):
            os.makedirs(os.path.dirname(self.directory + "downloads/" + inp[0]), exist_ok=True)
            f = open(self.directory + "downloads/" + inp[0],'wb')
            for i in range(0,len(inp[2])):
                    #user agent is not in compliance with Discord API rules. Change accordingly if needed
                    agent = {'User-Agent':'DiscordStorageBot (http://github.com/nigel/discordstorage)'}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(inp[2][i],headers=agent) as r:
                                if r.status == 200:
                                        async for data in r.content.iter_any():
                                                f.write(data)
            f.close()            #files[code] = [name,size,[urls]]

    #Uploads a file to the server from the root directory, or any other directory specified
    #inp = directory, code = application-generated file code
    #RUNS ON MAIN THREAD, ASYNC.
    async def async_upload(self,inp,code):
            urls = []
            f = open(inp,'rb')
            channel = self.session.getChannel()
            
            # Check if channel exists and is a messageable channel
            if channel is None:
                f.close()
                raise Exception("Channel not found - check your channel ID configuration")
            
            # Check if it's a text channel or DM channel that supports messaging
            if not isinstance(channel, (discord.TextChannel, discord.DMChannel, discord.GroupChannel)):
                f.close()
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
            
            start_time = time.time()
            uploaded_bytes = 0
            
            for i in range(0, total_chunks):
                    chunk_start_time = time.time()
                    
                    # Read chunk data
                    chunk_data = f.read(chunk_size)
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
                            print("✅", end="")
                            
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
                                print("\n❌ Upload cancelled by user")
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
                    print(f"✅ ({chunk_speed/1024/1024:.1f} MB/s)")
                    print(f"📈 Progress: {progress:.1f}% | Avg Speed: {avg_speed/1024/1024:.1f} MB/s | ETA: {self.calculate_eta(file_size - uploaded_bytes, avg_speed)}")
                    
                    if i < total_chunks - 1:  # Don't print separator after last chunk
                        print("   " + "█" * int(progress/2) + "░" * int(50-progress/2) + f" {uploaded_bytes}/{file_size} bytes")
            
            f.close()
            
            total_time = time.time() - start_time
            avg_speed = file_size / total_time if total_time > 0 else 0
            
            print("-" * 50)
            print(f"🎉 Upload completed!")
            print(f"⏱️  Total time: {total_time:.1f}s")
            print(f"🚀 Average speed: {avg_speed/1024/1024:.1f} MB/s")
            print(f"📋 File code: {code}")

            return [os.path.basename(inp),os.path.getsize(inp),urls]

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
