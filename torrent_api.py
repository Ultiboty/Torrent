from socket import *
import re

def set(sock: socket, server: str, address: tuple) -> bool:
    """ $ SET $ - USED BY ADMIN (Management Server)
    static function, sends the message to the connections server.
    :Purpose: to update the connections servers data base with the credentials of the server.

    Parameters:
    server: the servers NAME.
    sock: the SOCKET the servers uses.
    address: the IP & PORT of the connection (Management_server) itself.

    OUTPUT:
    Boolean - True / False (Based of the outcome of the process)
    """

    ret = False
    try:
        sock.send(f'POST: {server}-{address}'.encode('utf-8'))
        ret = True

    except Exception as e:
        print(f"Error occurred: {e}")
        ret = False
    finally:
        return ret


def get(class_ip: tuple, server_name: str) -> tuple:
    # create the socket
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect(class_ip)

    try:
        sock.send(f'GET: {server_name}'.encode('utf-8'))

        while True:

            data = sock.recv(1024).decode('utf-8')
            if not data:
                return False

            # fetch address
            return re.search('[\d\.]+', data).group(0), int(re.search('\d{5}', data).group(0))

    except Exception as e:
        # log the error
        print(f"Error occurred: {e}")
        return False
