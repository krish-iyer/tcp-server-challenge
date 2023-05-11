# Reliable TCP Server (WIP)

## Requirements: 

This project is built with Python 3.10.6. Although it should be supported with any Python3 release.

No additional module has been used. The project uses following modules(already installed with python 3.10.6 out of the box)

 - socket
 - select
 - logging
 - struct
 - ipaddress
 - math
 - argparse
 - configparser

## Launch server

To see all the command line arguments

```
python3 server_krishnan.py --help
```

The same arguments can be listed in a .cfg file and passed as an argument

```
python3 server_krishnan.py -c server_krishnan.cfg
```

Too confusing? simply run

```
python3 server_krishnan.py -c server_krishnan.cfg
```
or
```
python3 server_krishnan.py --ip '192.168.64.13' --port 8000 
```

## Communicate to server

Proxy Server is expecting 4 arguments IP, Port of the backend server and 2 numbers 
(datatype: double) "a" and "b". Proxy Server will validate the values and if everything goes good
it will contact backend server on the mentioned address and provide 4 arguments

 - IP   (of proxy server itself)
 - Port (of proxy server itself)
 - a ^ b
 - a / b

Now to communicate to Proxy server you need to frame data in following format. The first row in the below denotes size in bytes. Size of IP is calculated on the go. The header is fixed which is "$N>". 

The datasize is calculated as

```
1 (datasize) + X (IP) + 2 (Port) + 8 (num_a) + 8 (num_b) + 1 (checksum)
```

<table width="450">
  <thead>
    <tr>
      <th>3</th>
      <th>1</th>
      <th>X</th>
      <th>2</th>
      <th>8</th>
      <th>8</th>
      <th>1</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Header</td>
      <td>datasize</td>
      <td>Backend IP</td>
      <td>Backend Port</td>
      <td>num_a</td>
      <td>num_b</td>
      <td>checksum</td>
    </tr>
    <tr>
      <td>$N></td>
      <td>20+X</td>
      <td>eg. 192.168.21.3</td>
      <td>eg. 9000</td>
      <td>eg. 8.0</td>
      <td>eg. 4.0</td>
      <td>XOR(datasize - num_b)</td>
    </tr>
  </tbody>
</table>

Any bad frame will be rejected. On a successful operation the server will send '/x01' back(Success) to client and on failure b'' or b'/x00'(Failure) 

## Launch good client

See --help for more

```
python3 good_client_krishnan.py --help
```

To simply run 

```
python3 good_client_krishnan.py --ip $proxy_server_ip --backend_ip $backend_server_ip --backend_port $backend_port --num1 8.0 --num2 4.0
```
