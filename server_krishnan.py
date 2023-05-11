#!/usr/bin/python3

import socket
import select
import logging
import struct
import ipaddress
import math
import argparse
import configparser

'''
Class validation: It does validation of the packets over TCP

Functions:
 - validate_checksum : validate the checksum with the received checksum in the packet
                        
 - validate_packet   : validates length of the packet with the actual length, unpacks
                        and validates each element of data

 - validate_data     : validates if IP is in correct format and if it's not the server's IP 
                        which is invalid. 
'''
class validation:
    
    def __init__(self, logger, ip, port):
        self.logger = logger
        self.ip = ip
        self.port=port
    
    '''
    Function: validate_checksum
    Params:
        /data - packed data packet received in bytes format
        /pack_check - checksum received from the client in the packet.
    Return:
        True or False upon verification
    '''
    
    def validate_checksum(self, data, pack_check):
        checksum = 0
        data = b'$N>'+ data
    
        for i in range (len(data)-1) :
            checksum ^= data[i]
        
        if(checksum == pack_check):
            return True
        
        return False
    
    '''
    Function: validate_packet
    Params:
        /data_size   - size of the data(received in the packet) in byte fomat (b'')
        /data_size_i - size of the data(received in the packet) in int
        /data        - packet received
    Return:
        unpacked data or raise exception 
    '''
    
    def validate_packet(self, data_size, data_size_i, data):
        if(len(data) == data_size_i-1) and data_size_i != 0:
            if(self.validate_checksum(data_size+data, data[-1])):
                self.logger.debug("Packet checksum passed")
                # len(data) - 11 tries to calculate size of IP address string  
                # see more in item(bytes) format
                # 11 = (port(2) + num_a(8) + num_b(8) + checksum(1)) 
                unpack_data = struct.unpack('!%dsH2dB'%(len(data)-19), data) 
                if(self.validate_data(unpack_data) == True):
                    self.logger.debug("data has been validated")    
                    return unpack_data
                else:
                    self.logger.debug("data validation failed or wrong number of items received")
                    raise ValueError("data validation failed or wrong number of items received")
            else:
                self.logger.debug("packet checksum failed")
                raise ValueError("packet checksum failed")
        else:
            self.logger.debug("data size and claimed data size didn't match or zero")
            self.logger.debug("claimed data size : {} actual data : {}".format(data_size_i, len(data)))
            raise ValueError("packet length match failed")
    '''
    Function validate_data
    Params:
        /data - unpacked data, hopefully [IP, Port, Numa, Numb, checksum]
    Return:
        True or False 
    '''
    def validate_data(self, data):
                
        if(len(data) == 5):
            try:
                ipaddress.ip_address(data[0].decode("utf-8"))
            except ValueError:
                self.logger.debug("IP is wrong")
                return False
            
            if(self.ip == data[0].decode("utf-8")):
                return False
            
            self.logger.debug("IP is good")
            return True
        else:
            return False

'''
Class server(validation): Creates a TCP server using select(). The server keeps track of all    
                            connection but only cater one at time. Once the request is          
                            successful it sends back the response to client and closes the      
                            connection. On any bad request, server anyway closes the connection 

Functions:
 - run  : The main function which accepts the connection, validates the data and send to the server
 
 - sent_to_server : perform operation (numa ^ numb) and (numa/numb) and send to server requested
                    in the received packet

 - oper : perfrom mathematical operation
'''

class server(validation):
    
    def __init__(self, ip, port, backlog, loglevel, select_timeout, num_conn, send_to_server_timeout, recv_buffer_size):
        
        self.ip = ip
        self.port = port
        self.backlog = backlog
        self.select_timeout = select_timeout
        self.num_conn=num_conn
        self.send_to_server_timeout = send_to_server_timeout
        self.recv_buffer_size = recv_buffer_size
        # Setup logger
        self.logger = logging.getLogger('server_log')
        self.logger.setLevel(loglevel)
        
        self.loghandle = logging.StreamHandler()
        self.loghandle.setLevel(loglevel)
        
        self.loghandle.setFormatter(logging.Formatter(('%(asctime)s - [%(name)s] - [%(levelname)s] - %(message)s')))
        self.logger.addHandler(self.loghandle)
        
        # Setup server socket
        # Throws an error if IP is not valid
        self.srv=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,10)
        self.srv.bind((self.ip,self.port))
        self.srv.listen(self.backlog)

        # setup client
        self.cli=None
        #associate each socket to its address info
        self.clisocks={}
        
        
        
    '''
    Function : oper
    Params
        \data : [numa, numb]
    Return:
        [numa^numb, numa/numb]
    '''
    def oper(self, data):
        
        oper_b = math.pow(abs(data[0]),data[1])     # data correction if base value is negative
        
        if(data[1] != 0):
            oper_a = data[0] / data[1]
        else:
            oper_a = 0    
    
        return [oper_a, oper_b]
    '''
    Function: send_to_server
    Params:
        /data : [ClientIP, ClientPort, numa, numb, checksum]
    Return:
        True or False : if data has been successfully sent. 
    '''
    def send_to_server(self, data):

        try:
            n_a, n_b = self.oper(data[2:4])
            self.logger.debug("New calculation completed n_a : {} n_b: {}".format(n_a,n_b))
        except ValueError:
            self.logger.error("Couldn't do operations on number")
            return False        

        try:
            # pack the data [ClientIP, Client Port, numa^numb, numa/numb]
            pack_to_send = struct.pack('!2d%dsH'%len(self.ip.encode("utf-8")),n_a, n_b, self.ip.encode("utf-8"), self.port)
            # create a client socket to send the data
            self.cli=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            # set timeout for how long you can wait to connect to server
            self.cli.settimeout(self.send_to_server_timeout)
            self.cli.connect((data[0].decode("utf-8"),data[1]))
            self.cli.sendall(pack_to_send)
            # close the socket
            self.cli.close()
            self.logger.info("Sent packet to server {}".format(data[:2]))
            return True
        except Exception as e:
            self.logger.error("Couldn't send packet to server {}".format(data[:2]))
            self.logger.debug("exception raised: {}".format(e))
            self.cli.close()
            return False

    '''
    Function run:
    Params:
        None
    Return:
        None
    '''
    def run(self):
        try:
            while True:
                r,w,x=select.select([self.srv]+list(self.clisocks.keys()),[],[],self.select_timeout)
  
                if self.srv in r and (len(self.clisocks) <= self.num_conn) :            # donot accept new connections if already full
                    conn,addr=self.srv.accept()
                    self.logger.info("New connection from {}".format(addr))
                    self.clisocks[conn]=addr
                
                for conn in [i for i in r if i!=self.srv]:
                    self.logger.debug("There is something to read from {}".format(conn))
                    recv_packet=conn.recv(self.recv_buffer_size)                                         # receive header
                    header = recv_packet[:3]
                    if header:
                        if(header.find(b'$N>')) != -1:                                  # check if header is right
                            data_size = recv_packet[3:4]                                # data_size in b'' format
                            data_size_i = int.from_bytes(data_size, 'little')           # int of data_size ; endian doesn't matter
                            if(data_size_i != 0):
                                data = recv_packet[4:(data_size_i)+4]                   # receive data of mentioned size
                            else:
                                data = b''
                            try:
                                unpack_data = self.validate_packet(data_size,data_size_i,data)  # validate packet
                                self.logger.info("Packet has been validated")
                                self.logger.debug("received data{}".format(unpack_data))
                                self.logger.critical("Received data from client - IP: {} ; Port {} ; NumA: {} ; NumB: {}".format(unpack_data[0], unpack_data[1], unpack_data[2], unpack_data[3]))
                                conn.send(self.send_to_server(unpack_data).to_bytes(1,"little")) # send to the server requested by client
                            except ValueError:
                                self.logger.error("Packet validation failed")
                                self.logger.error("Closing connection - Packet incompatible")
                                conn.close()
                                self.clisocks.pop(conn)                           
                        else:
                            self.logger.error("Wrong packet header")
                            conn.close()
                            self.clisocks.pop(conn)
                    else:
                        self.logger.debug("dropped connection from {}".format(self.clisocks[conn]))
                        self.clisocks.pop(conn)

                self.logger.debug("We have {} clients connected so far".format(len(self.clisocks)))
                
        except KeyboardInterrupt:
            self.logger.critical("Exiting on user interrupt(ctrl-c)!")
            for conn in r:
                conn.close()
        except Exception as e:
            self.logger.error("Something bad happened")
            for conn in r:
                conn.close()


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Secure TCP Server", \
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-c","--conf_file", type=str, help="config file")
    parser.add_argument("--ip", type=str, help="IP")
    parser.add_argument("--port", default=8000, type=int, help="port")
    parser.add_argument("--backlog", default=1, type=int, help="number of unaccepted connections")
    parser.add_argument("--log_level", default=50, type=int, choices=[50,40,30,20,10,0], help="CRITICAL = 50 \
                                                                    \r\n ERROR = 40  \
                                                                    \r\n WARNING = 30 \
                                                                    \r\n INFO = 20 \
                                                                    \r\n DEBUG = 10 \
                                                                    \r\n NOTSET = 0")
    parser.add_argument("--select_timeout", default=None, type=float, help="number of unaccepted connections")
    parser.add_argument("--conn", default=10, type=int, help="number of connections that can be accepted" )
    parser.add_argument("--send_to_server_timeout", default=0.1, type=float, help="Connection timeout to server to which \
                            data has be sent" )
    parser.add_argument("--recv_buffer_size", default=1024, type=int, help="Server Recieve buffer size")
    args = parser.parse_args()
  
    if(args.conf_file):
        conffile = configparser.ConfigParser()
        conffile.read(args.conf_file)
        defaults = {}
        defaults.update(dict(conffile.items("DEFAULT")))
        parser.set_defaults(**defaults)
        args = parser.parse_args()

    if(args.ip):
        try:
            serverObj = server(args.ip, args.port, args.backlog, args.log_level, \
                                args.select_timeout, args.conn, args.send_to_server_timeout, args.recv_buffer_size)
            serverObj.run()
        except Exception as e:
            print("There's a problem with you server configuration! Couldn't start sever")
            #print(e)
    else:
        print("You haven't provided an IP to start the server!")
