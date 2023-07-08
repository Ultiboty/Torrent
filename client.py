import torrent_api
import threading
from socket import *
import select
import re
import os
import time


def get_open_port():
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


class Client:
    def __init__(self, MS_addr):
        # set up the socket
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.connect(MS_addr)

        # create the peer
        self.peer = Peer()

        # handshake with server
        self.sock.send(f'up {self.peer.addr}'.encode('utf-8'))

        print('peer', self.peer.addr)

        receive_thread = threading.Thread(target=self.peer.receive_files)
        receive_thread.start()

        # server comms
        while True:

            msg = str(input("Try chatting with the server... - "))
            self.sock.send(msg.encode('utf-8'))
            if msg[0:7] == '/upload':
                # get file name
                msg.strip()
                f_name = msg[8:len(msg)]
                # get active clients
                data = self.sock.recv(1024).decode('utf-8')
                self.peer.upload(data,f_name)
            data = self.sock.recv(1024).decode('utf-8')
            if not data: break
            print("Admin: ", data)


class Peer:
    def __init__(self):
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.addr = ('192.168.0.106', get_open_port())
        self.sock.bind(self.addr)
        self.sock.listen(2)

    def disconnect_user(self, inputs, outputs, s,f_dict):
        f_dict[s]["file"].close
        print(s.getpeername(), 'is exiting the session')
        # remove from inputs/outputs
        inputs.remove(s)
        outputs.remove(s)
        s.close()

    def upload(self, addresses, file_name):
        addresses = re.findall("\('[\d\.]+', \d+, \d\)", addresses)  # "\d+: \('[\d\.]+', \d+\)" for including the id num
        for i in range(len(addresses)):
            addresses[i] = (re.search('[\d\.]+', addresses[i]).group(0), int(re.search('\d{5}', addresses[i]).group(0)))
        print(addresses)
        addresses.remove(self.addr)
        parts = len(addresses)
        size = os.stat(file_name).st_size
        segment = 0
        for address in addresses:
            # connect to the peer
            temp_sock = socket(AF_INET, SOCK_STREAM)
            temp_sock.connect(address)

            # upload the file
            f = open(file_name, 'rb')
            d = f.read(4096)

            temp_sock.send(f'hi peer!\n{file_name}\n0\n{os.stat(file_name).st_size}'.encode('utf-8'))
            while d:
                print('Sending...')
                temp_sock.send(d)
                d = f.read(4096)
            f.close()
            print("Done Sending")
            temp_sock.shutdown(SHUT_WR)
            temp_sock.close()

    def receive_files(self):
        inputs = [self.sock]  # list of connections we receive messages/requests from
        outputs = []  # list of the messages we are sending
        file_dict = {}
        while inputs:
            readable, writable, exceptional = select.select(inputs, outputs, [])
            # go through every readable sock
            for s in readable:

                # accept the new user
                if s is self.sock:
                    connection, client_address = s.accept()
                    inputs.append(connection)
                    outputs.append(connection)
                # the sock is client socket
                elif s not in file_dict.keys():
                    data = s.recv(1024).decode('utf-8')
                    # check for handshake
                    if data[0:8] == 'hi peer!':
                        data = data.split('\n')
                        file_dict[connection] = {
                            "file": open(f'{data[1]}', 'wb'),
                            "file_name": data[1],
                            "min_segment": data[2],
                            "max_segment": data[3],
                            "path": None
                        }
                else:
                    # try receiving the data from the client
                    try:
                        data = s.recv(4096)
                        if not data:
                            self.disconnect_user(inputs, outputs, s,file_dict)
                        else:
                            file_dict[s]["file"].write(data)

                    # in case of exception, disconnect the user
                    except Exception as e:
                        print(e)
                        self.disconnect_user(inputs, outputs, s,file_dict)

            # disconnect every socket in the exceptions
            for s in exceptional:
                self.disconnect_user(inputs, outputs, s,file_dict)
        self.sock.close()


if __name__ == '__main__':
    class_server_ip = ('192.168.0.106', 60000)
    server_name = 'OMER'
    ms_addr = torrent_api.get(class_server_ip, server_name)
    print(ms_addr)
    if not ms_addr:
        raise "Error in API"
    client = Client(MS_addr=ms_addr)

