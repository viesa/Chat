import socket
import select
import errno
import sys
import threading
import time
import pickle

HEADERSIZE = 10
QUERYSIZE = 10
IP = "localhost"
PORT = 1234


class Client:
    def __init__(self):
        self.is_active = True
        self.is_connected = False
        self.new_status = False
        self.status = ""
        self.token = ""
        self.new_messages = []
        self.new_clients = []
        self.del_clients = []

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sending_list = []

        self.worker = threading.Thread(target=self.mgr)
        self.worker.start()

    def init_connection(self):
        try:
            self.client_socket.connect((IP, PORT))
        except:
            return False
        else:
            self.client_socket.setblocking(False)
            self.is_connected = True
            return True

    def mgr(self):
        while self.is_active:
            if self.is_connected:
                self.send_all_pending_packages()
                while self.handle_new_requests():
                    pass
            else:
                time.sleep(0)

    def add_send(self, query, data):
        if data:
            pickled_data = pickle.dumps(data)
            packet = {
                "data": pickled_data,
                "query": f"{query:<{QUERYSIZE}}".encode("utf-8"),
                "header": f"{len(pickled_data):< {HEADERSIZE}}".encode("utf-8"),
            }
            self.sending_list.append(packet)
            return True
        else:
            return False

    def receive_message(self):
        try:
            message_header = self.client_socket.recv(HEADERSIZE)
            if not len(message_header):
                self.is_connected = False
                self.client_socket.close()
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.token = ""
                return False

            message_query = self.client_socket.recv(QUERYSIZE)
            if not len(message_query):
                return False

            message_length = int(message_header.decode("utf-8").strip())
            message_query = message_query.decode("utf-8").strip()
            return {
                "header": message_header,
                "query": message_query,
                "data": pickle.loads(self.client_socket.recv(message_length)),
            }
        except IOError as e:
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                print("Reading error", str(e))
                sys.exit()
            return False
        except Exception as e:
            print("General error", str(e))
            sys.exit()
            return False

    def handle_new_requests(self):
        incoming = self.receive_message()
        if not incoming:
            return False

        query = incoming["query"]
        data = incoming["data"]

        if query == "AUTH":
            success = data["success"]
            reason = data["reason"]
            self.new_status = True
            self.status = reason
            if success:
                self.token = data["token"]
        elif query == "CHATUPT":
            username = data["username"]
            message = data["message"]
            chat_color = data["chat_color"]
            self.new_messages.append(
                {"username": username, "message": message, "chat_color": chat_color,}
            )
        elif query == "USRSNEW":
            self.new_clients = data.copy()
        elif query == "USRSDEL":
            self.del_clients = data.copy()

        return True

    def send_all_pending_packages(self):
        for packet in self.sending_list:
            self.client_socket.send(packet["header"] + packet["query"] + packet["data"])
        self.sending_list.clear()


if __name__ == "__main__":
    client = Client()
    client.mgr()
