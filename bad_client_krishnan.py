#!/usr/bin/python3

import socket
import struct
import argparse

class client:
    
    def __init__(self, ip, port, backend_ip, backend_port, num_a, num_b):
        self.ip = ip
        self.port = port
        self.num_a = num_a
        self.num_b = num_b
        self.cli = None
        self.backend_ip = backend_ip
        self.backend_port = backend_port
        
    def calc_checksum(self,data):
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum
        
    def create_pack(self, ip_a, port_a, num_a, num_b):
        # 14 - ip - 'xxx.xxx.xx.xxx'
        # 8  - len(int)*2
        # 3  - header
        # 2  - port
        # 1  - checksum
        checksum = 0
        pack_data = struct.pack('!3sB%dsH2d'%len(ip_a),b'$N>', 1+2*8+2+len(ip_a)+1, ip_a, port_a, num_a, num_b)
        checksum = self.calc_checksum(pack_data)

        pack_data_with_checksum = struct.pack('%dsB'%len(pack_data), pack_data, checksum)
        return pack_data_with_checksum 

    def un_pack(self, data):
        return struct.unpack('!3sB%dsH2dB'%(len(data)-23), data)
    
    def send_to_server(self, data, recv, close):
        cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli.connect((self.ip, self.port))
        cli.sendall(data)
        if(recv == True):
            ret=cli.recv(1024)
            print(ret)
        if(close == True):
            cli.close()

    def attack(self):
        data = self.create_pack(self.backend_ip.encode("utf-8"), self.backend_port, self.num_a, self.num_b)
        self.send_to_server(b'', False, False)
        self.send_to_server(b'/x00/x01', True, True)        
        self.send_to_server(b'192.168.64.1'+ int(9000).to_bytes(4, "big")+ int(0).to_bytes(4, "big")+ int(0).to_bytes(4, "big"), True, True)
        self.send_to_server(b'192.168.64.1'+ int(8589934592).to_bytes(8, "big")+ int(0).to_bytes(4, "big")+ int(0).to_bytes(4, "big"), True, True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bad Client", \
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument("--ip", type=str, help="IP")
    parser.add_argument("--port", default=8000, type=int, help="port")
    parser.add_argument("--backend-ip", type=str, help="backemd IP")
    parser.add_argument("--backend-port", default=9000, type=int, help="backend port")
    parser.add_argument("--num1", default=2,type=int, help="num1")
    
    parser.add_argument("--num2", default=3, type=int, help="num2")
    
    args = parser.parse_args()

    cliObj = client(args.ip, args.port, args.backend_ip, args.backend_port, args.num1, args.num2)
    cliObj.attack()