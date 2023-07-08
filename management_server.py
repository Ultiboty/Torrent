from socket import *
import subprocess
import re
import torrent_api
import sqlite3 as lite
import select
from tabulate import tabulate

#
#
#
# im not using it for now cus i dont wanna copy too ,uch from daniel
def server_credentials():
    """
    RETURNS: the credentials of the server -> (IP, PORT)
    1. uses subprocess to fetch the ip + string manipulation.
    2. uses the following 'port' code in order to find the first OPEN port on the device - (SERVER).
    """

    data = subprocess.check_output('ipconfig').decode('utf-8')
    data = re.sub(r'[^\w\n|.]', '', data)

    k = data.index("IPv4Address") + 1  # the index of the ip address.
    ip = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?=\s|\Z)', data[k: data.index('\n', k)])
    ip = ip.group(0) if ip is not None else None

    # PORT
    scan_socket = socket(AF_INET, SOCK_STREAM)
    scan_socket.bind(("", 0))
    scan_socket.listen(1)

    port = scan_socket.getsockname()[1]
    scan_socket.close()

    return ip, port


class ManagementServer:
    def __init__(self, MS_addr, class_addr, server_name):
        # set up users database
        self.db_users = 'ms_data_base_users.db'
        self.conn_users = self.set_sql_db_users()

        # set up file database
        self.db_files = 'ms_data_base_files.db'
        self.conn_files = self.set_sql_db_files()

        # set up server
        self.addr = MS_addr
        self.sock = socket(AF_INET, SOCK_STREAM)

        # Update the connections' server.
        self.update_connections_server(class_addr, server_name)

        self.sock.bind(self.addr)
        self.sock.listen(2)
        print(f"Server is up at: {self.sock.getsockname()}")
        self.handle_clients()

    def update_connections_server(self, class_addr, name) -> None:
        try:
            TCP_sock = socket(AF_INET, SOCK_STREAM)
            TCP_sock.connect(class_addr)
            process_result = torrent_api.set(TCP_sock, name, self.addr)
            if not process_result:
                raise 'Error in API'
            TCP_sock.close()
        except Exception as e:
            raise e

    def set_sql_db_files(self):
        try:
            conn = lite.connect(self.db_files)
            cursor = conn.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS clients (
                file_name TEXT,
                segment TEXT,
                holder_name TEXT
                )"""
                           )
            conn.commit()
            return conn
        except Exception as e:
            raise (e)

    def set_sql_db_users(self):
        try:
            conn = lite.connect(self.db_users)
            cursor = conn.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS clients (
                peer_ip TEXT,
                peer_port INT,
                status BOOL
                )"""
                           )
            conn.commit()
            return conn
        except Exception as e:
            raise (e)

    def disconnect_user(self, inputs, outputs, s):
        print(s.getpeername(), 'is exiting the session')

        # change status in database to false
        curser = self.conn_users.cursor()
        update = """UPDATE clients SET status = FALSE WHERE peer_ip = ?"""
        curser.execute(update, (s.getpeername()[0],))
        self.conn_users.commit()

        # remove from inputs/outputs
        inputs.remove(s)
        outputs.remove(s)
        s.close()

    def save_new_users(self, ip, port):
        curser = self.conn_users.cursor()
        curser.execute("SELECT * FROM clients WHERE peer_ip = ?",(ip,))
        existing = curser.fetchall()
        if not existing:
            curser.execute("""INSERT INTO clients (peer_ip, peer_port, status) VALUES (?,?,?) """, (ip, port, True))
        else:
            curser.execute("""UPDATE clients SET status = TRUE WHERE peer_ip = ?""", (ip,))
            curser.execute("""UPDATE clients SET peer_port = ? WHERE peer_ip = ?""", (port,ip,))
        self.conn_users.commit()

    def get_active_clients(self):
        curser = self.conn_users.cursor()
        curser.execute("SELECT * FROM clients WHERE status = TRUE")
        return curser.fetchall()

    def handle_clients(self):
        inputs = [self.sock]  # list of connections we receive messages/requests from
        outputs = []  # list of the messages we are sending
        while inputs:
            readable, writable, exceptional = select.select(inputs, outputs, [])
            # go through every readable sock
            for s in readable:

                # accept the new user
                if s is self.sock:
                    connection, client_address = s.accept()
                    print("starting session from:", client_address)
                    inputs.append(connection)
                    outputs.append(connection)
                # the sock is client socket
                else:
                    # try receiving the data from the client
                    try:
                        data = s.recv(1024).decode('utf-8')
                        print('received:', data, 'from:', s.getpeername())

                        # if the user wants to exit, disconnect him
                        if not data or data == 'exit':
                            self.disconnect_user(inputs, outputs, s)

                        # handshake for client who connected
                        elif data[0:2] == 'up':
                            self.save_new_users(re.search('[\d\.]+', data).group(0), int(re.search('\d{5}', data).group(0)))

                        elif s in writable:
                            if data[0:7] == '/upload':
                                users = self.get_active_clients()
                                s.send(str(users).encode('utf-8'))

                    # in case of exception, disconnect the user
                    except Exception as e:
                        print(e)
                        self.disconnect_user(inputs, outputs, s)

            # disconnect every socket in the exceptions
            for s in exceptional:
                self.disconnect_user(inputs, outputs, s)
        self.sock.close()
        self.conn_users.close()


if __name__ == '__main__':
    class_server_addr = ('192.168.0.106', 60000)
    name = 'OMER'
    ms_addr = ('192.168.0.106', 55000)
    # MS_addr = server_credentials()
    ms = ManagementServer(MS_addr=ms_addr,class_addr=class_server_addr,server_name=name)
