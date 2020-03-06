import aiohttp
import asyncio
import json
import logging
import re
import sys
import time
#used to store client info
client_cache = {}
#Google Places APU
GOOGLE_PLACES_API_URL ='https://maps.googleapis.com/maps/api/place/nearbysearch/json?'
#API_KEY
# TODO: PLACE YOUR GOOGLE PLACES API KEY HERE
API_KEY= ''
#Server IDs
SERVER_ID= ['Hill', 'Jaquez', 'Smith', 'Campbell', 'Singleton']
#Server Communication, it's bidirectional
 #change the port to your desired ports
SERVER_COMMUNICATION= {
    'Hill':['Jaquez', 'Smith'],
    'Jaquez':['Hill','Singleton'],
    'Smith':['Campbell','Hill'],
    'Campbell':['Smith','Singleton'],
    'Singleton':['Jaquez', 'Smith', 'Campbell']
}
IP_ADDRESS= '127.0.0.1'
#ports to be used on UCLA Server

#Ports for local use
 PORTS= {
   'Hill' : 8000,
   'Jaquez' : 8001,
   'Smith' : 8002,
   'Campbell' : 8003,
   'Singleton' : 8004
 }
# Protocol Factrory CLASS
class EchoServerProtocol(asyncio.Protocol):
    #constructor
    def __init__(self, command_server_id, event_loop):
        self.loop= event_loop
        self.server_id= command_server_id
        self.message= ""
        self.peername= None   
    #--------------- create a new connection ------------
    def connection_made(self, transport):
        #Return information about the transport or underlying resources it uses
        self.peername = transport.get_extra_info('peername')
        # write in the log
        logging.info('Connection made: {}'.format(self.peername))
        print('Connection made {}'.format(self.peername))
        self.transport = transport
    #process data
    def data_received(self, data):
        #decode the data
        data_decoded= data.decode()
        # write in the log
        logging.info('Received data: {!r}'.format(data_decoded))
        print('Data received: {!r}'.format(data_decoded))
        #------------------- start processing the data
        #split the message to grab different parts
        self.message=data_decoded
        #print("sef message {}".format(self.message))
        messageArr =  self.message.split()
        messageCode = messageArr[0]
        #print("code {}".format(messageCode))
        payload = messageArr[1:]
        #  Process IAMAT command
        if messageCode == 'IAMAT' and self.iamat_validator(payload):
            logging.info("Starting to Process IAMAT {}".format(payload))
            self.iamat_code(payload)
        #  Process WHATSAT command
        elif messageCode == 'WHATSAT' and self.whatsat_validator(payload):
            logging.info("Starting to Process WHATSAT {}".format(payload))
            self.whatsat_code(payload)
        #  Process AT command
        elif messageCode == 'AT' and self.at_validator(payload):
            logging.info("Starting to Process AT {}".format(payload))
            self.at_code(payload)
        #  Process INVALID command
        #Servers should respond to invalid commands with a line that contains a question mark (?), a space, and then a copy of the invalid command.
        else:
            #format the invalid response as the assigment spec
            invalid_response = '? {}\n'.format(messageArr)
            self.transport.write(invalid_response.encode())
            logging.info('Invalid Data sent: {!r}'.format( invalid_response))
    # Servers communicate to each other too, using AT messages (or some variant of your design) to implement a simple
    #  flooding algorithm to propagate location updates to each other
    #NOTE: This is not by me, found on stackover-flow
    def iamat_validator(self, payload):
        #  Verify arg length
        if len(payload) != 3:
            print("Error: Invalid number of args for IAMAT")
            return False
        location = payload[1]
        time = payload[2]
        #  Verify location
        if not re.fullmatch('[+-]\d*\.?\d+[+-]\d*\.?\d+', location):
            logging.info("location string is invali")
            return False
        coordination= re.split('[+-]', location[1:])
        latitude, longitude = float(coordination[0]), float(coordination[1])
        #check for long and lat bound
        if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
            logging.info("lat or long or both are invalid; out of bound")
            print("Invalid location format")
            return False
        #validate time
        try:
            float(time)
        except ValueError:
            logging.info("Invalid time format {}".format(time))
            print("Invalid time format")
            return False
        #passed all the validations, return true
        return True
    def whatsat_validator(self, payload):
         #  Verify arg length
        if len(payload) != 3:
            logging.info("Invalid number of args for WHATSAT")
            print("Invalid number of args for WHATSAT")
            return False
        client_id = payload[0]
        radius = payload[1]
        num_results = payload[2]
        #  Verify client
        if client_id not in client_cache.keys():
            print("Invalid client ID")
            return False
        # validate rad and num of result
        try:
            radius = int(radius)
            num_results = int(num_results)
        except ValueError:
            logging.info("Invalid radius/results type")
            print("Invalid radius/results type")
            return False
        if radius < 0 or radius > 50 or num_results < 0 or num_results > 20:
            logging.info("Radius/num_results out of bounds")
            print("Radius/num_results out of bounds")
            return False
        return True
    #validate AT
    def at_validator(self, payload):
        #  Verify arg length
        if len(payload) != 6:
            logging.info("Invalid number of args for AT")
            print("Invalid number of args for AT")
            return False
        server_id = payload[0]
        client_location = payload[3]
        client_time = payload[4]
        #  Verify server ID
        if server_id not in SERVER_ID:
            print("Invalid server ID")
            return False
        #  Verify arg info
        if not re.fullmatch('[+-]\d*\.?\d+[+-]\d*\.?\d+', client_location):
            logging.info("location string is invali")
            return False
        coordination= re.split('[+-]', client_location[1:])
        latitude, longitude = float(coordination[0]), float(coordination[1])
        #check for long and lat bound
        if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
            logging.info("lat or long or both are invalid; out of bound")
            print("Invalid location format")
            return False
        #validate time
        try:
            float(client_time)
        except ValueError:
            logging.info("Invalid time format {}".format(client_time))
            print("Invalid time format")
            return False
        return True
    #using the flooding algorithm to open a connection and flood to neighbors
    async def flooding(self, message, senders):
        for neighbor in SERVER_COMMUNICATION[self.server_id]:
            if neighbor not in senders:
                try:
                    #Flood to neighbor
                    port = PORTS[neighbor]
                    reader, writer = await asyncio.open_connection(host=IP_ADDRESS, port=port, loop=self.loop)
                    writer.write(message.encode())
                    await writer.drain()
                    writer.close()
                    print('Flooded data to {}'.format(neighbor))
                    logging.info('Flooded data to {}'.format(neighbor))
                #if failed to flood
                except ConnectionRefusedError:
                    print('Flooded data to {}'.format(neighbor))
                    logging.info('Flooded to {} failed'.format(neighbor))
    #function to update the cache
    def update_cache(self, client_id, updated_client_info):
        cached_info = client_cache.get(client_id)
        #if client info already exist in the cache
        if cached_info is not None:
            if cached_info== updated_client_info:
                logging.info("Client {} is up to date".format(client_id))
                return False
            #  Client info is stale
            cached_time = cached_info[3]
            if float(cached_time) >= float(updated_client_info[3]):
                logging.info('Client {}\'s info is stale'.format(client_id))
                return False
        #if client info is new
        client_cache[client_id]= updated_client_info
        logging.info("new client {} added to cache".format(client_id))
        return True
    #process IAMAT
    def iamat_code(self, payload):
        #decompose the payload to its elemtns
        client_id= payload[0]
        coordinate= payload[1]
        timestamp= payload[2]
        # time stuff
        time_diff = time.time() - float(timestamp)
        if time_diff > 0:
            time_diff_str = '+' + str(time_diff)
        else:
            #but it might be negative if there was enough clock skew in that direction.
            time_diff_str = str(time_diff)
        #  Format AT message for the server response
        server_response_AT = 'AT {} {} {} {} {}\n'.format(self.server_id, time_diff_str, client_id, coordinate, timestamp)
        #  Send response to client
        self.transport.write(server_response_AT.encode())
        logging.info('Data sent to the client: {!r}'.format(server_response_AT))
        #  Update cache
        new_client_info = [self.server_id, time_diff_str, coordinate, timestamp]
        #  Propagate client info to neighbors
        if self.update_cache(client_id, new_client_info):
            #format the response
            message = 'AT {} {} {} {} {} {}\n'.format(self.server_id, time_diff_str, client_id, coordinate, timestamp, self.server_id)
            logging.info('Trying to flood client: {}'.format( message))
            print('trying to flood client: {}'.format( message))
            #Schedule the execution of a Coroutines. Return a Task object.
            self.loop.create_task(self.flooding(message, []))
    #fetch function based on aiohttp documentation
    async def fetch(self,session, url):
        async with session.get(url, ssl=False) as response:
            return await response.text()
    async def google_API_Request(self, location, radius, num_results):
        #based on the google APi call format the string
        google_URL= '{}location={}&radius={}&key={}'.format(GOOGLE_PLACES_API_URL, location, radius, API_KEY)
        #do http request using aiohttp
        #based on the documentation
        async with aiohttp.ClientSession() as session:
            html = await self.fetch(session, google_URL)
            print("html {}".format(html))
            #deserialzie and serialzing the HTML response
            deserialized_response = json.loads(html)
            deserialized_response['results'] = deserialized_response['results'][:num_results]
            serialized_response = '{}\n\n'.format(json.dumps(deserialized_response, indent=2))
            #send to the server
            self.transport.write(serialized_response.encode())
            #log
            logging.info('Google Data received: {!r}'.format(serialized_response))
    #Process WHATSAT
    #Clients can ask what is near one of the clients
    def whatsat_code(self, payload):
        #decompose the payload to its elemtns
        print("in whatsat")
        client_name= payload[0]
        radius=int(payload[1])*1000# in meter
        maxNumberOfResults= int(payload[2])
        client_server = client_cache[client_name][0]
        client_time_diff = client_cache[client_name][1]
        client_location = client_cache[client_name][2]
        client_time = client_cache[client_name][3]
        #  Format AT message
        at_response = 'AT {} {} {} {} {}\n'.format(client_server, client_time_diff, client_name, client_location, client_time)
        #send the respons to the client
        self.transport.write(at_response.encode())
        #  Format latitude and longitude
        coords = re.split('[+-]', client_location[1:])
        latitude = float(coords[0]) * (1 if client_location[0] == '+' else -1)
        longitude = float(coords[1]) * (1 if ('+' in client_location[1:]) else -1)
        latitude_and_longitude = '{},{}'.format(latitude, longitude)
        #  Google Places API
        # create corutine for it
        #neighbors don't share location
        self.loop.create_task(self.google_API_Request(latitude_and_longitude, radius, maxNumberOfResults))
    #Process AT
    def at_code(self, payload):  
        #decompose the payload to its elemtns
        source_server = payload[0]
        time_diff = payload[1]
        client_id = payload[2]
        client_location = payload[3]
        client_time = payload[4]
        client_server = payload[5]
        #  Propagate client info to neighbors
        if self.update_cache(client_id, [source_server, time_diff, client_location, client_time]):
            message = 'AT {} {}\n'.format(' '.join(payload[:-1]), self.server_id)
            logging.info('Flood client info: {}'.format( message))
            # create a coroutine task
            self.loop.create_task(self.flooding(message, [source_server, client_server]))
        # lost connection
    def connection_lost(self, exc):
        print('The server closed the connection')
        # write in the log
        logging.info('The server closed the connection: {}'.format(self.peername))
    
#-----------------SERVER IMPLEMENTATION-----------------
#start of the application
if __name__ == "__main__":
    #first read the command
    #do a few checks before start processing the othe things
    if len(sys.argv)!=2:
        print("Incorrect number of arguments to process")
        #exit with error code 1
        sys.exit(1)
    #check if the second arg is not one of the SERVER_IDs
    if sys.argv[1] not in SERVER_ID:
        print("The server ID is not a correct server ID")
        #exit with error code 1
        sys.exit(1)
    #store the server_id
    command_server_id= sys.argv[1]
    #  Create logger 
    logging.basicConfig(filename='{}.log'.format(command_server_id),
                        filemode='w',
                        format='%(asctime)s %(levelname)s %(message)s',
                        level=logging.INFO)
    #  Get the current event loop
    event_loop = asyncio.get_event_loop()
    #  Each client connection will create a new protocol instance
    #  loop.create_server(protocol_factory, host=None, port=None, *, family=socket.AF_UNSPEC, 
    #                     flags=socket.AI_PASSIVE, sock=None, backlog=100, ssl=None, reuse_address=None, 
    #                     reuse_port=None, ssl_handshake_timeout=None, start_serving=True)
    protocol_instance = event_loop.create_server(lambda: EchoServerProtocol(command_server_id, event_loop),
                                IP_ADDRESS, PORTS[command_server_id])
    #Run until the future (an instance of Future) has completed.
    server = event_loop.run_until_complete(protocol_instance)
    #  write in the log also print until 'Ctlr+C'
    #FORMAT: 2020-03-03 13:04:40,654 INFO Serving server Hill on ('127.0.0.1', 8000)
    print('Serving {} on (IP, PORT): {}'.format(command_server_id, server.sockets[0].getsockname()))
    logging.info('Serving {} on (IP, PORT): {}'.format(command_server_id, server.sockets[0].getsockname()))
    try:
        event_loop.run_forever()
    except KeyboardInterrupt:
        pass
    # close the server
    server.close()
    event_loop.run_until_complete(server.wait_closed())
    event_loop.close()
  
