import asyncio
import time
import sys
#invoke Hill with async
async def client_Hill(loop):
    #change the port to your desired port
	reader, writer = await asyncio.open_connection('127.0.0.1', 8000, loop=loop)
	try:
		cmd1 = 'IAMAT kiwi.cs.ucla.edu +34.068930-118.445127 1520023935.918963997\n'
		cmd2 = 'WHATSAT kiwi.cs.ucla.edu 10 5\n'
		#IAMAT COMMAND
		writer.write(cmd1.encode())
		await writer.drain()
		# writer.write_eof()
		while not reader.at_eof():
			data = await reader.read(50000)
			print('%s' % data.decode())
			break
		#WHATSAT COMMAND
		time.sleep(2)
		writer.write(cmd2.encode())
		await writer.drain()
		while not reader.at_eof():
			data = await reader.read(50000)
			print('%s' % data.decode())
			break
    #interupt if keyinterupt
	except KeyboardInterrupt:
		pass
#get loop and run intil complete
loop = asyncio.get_event_loop()
loop.run_until_complete(client_Hill(loop))
loop.close()










