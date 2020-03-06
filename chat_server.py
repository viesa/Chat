import socket
import select
import hashlib
import requests
import json
import time
import secrets
import random
import pickle


HEADERSIZE = 10
QUERYSIZE = 10
IP = "localhost"
PORT = 1234

base_url = "https://databas-8c8d.restdb.io/rest/credentials"
headers = {
    "content-type": "application/json",
    "x-apikey": "45c1dafe70a410f56d197c98c5a88b2e8b79c",
    "cache-control": "no-cache",
}


def sha256(string):
    hash_object = hashlib.sha256(bytes(string, "utf-8"))
    return hash_object.hexdigest()


class Server:
    def __init__(self):
        self.is_active = True

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((IP, PORT))
        self.server_socket.listen()

        self.socket_list = [self.server_socket]
        self.clients = {}

        self.new_clients = []
        self.del_clients = []

    def mgr(self):
        while self.is_active:
            if len(self.new_clients):
                self.broadcast_new_clients()
            if len(self.del_clients):
                self.broadcast_del_clients()

            read_sockets, _, exception_sockets = select.select(
                self.socket_list, [], self.socket_list
            )

            for notified_socket in read_sockets:
                if notified_socket == self.server_socket:
                    if not self.handle_new_connection():
                        continue
                else:
                    if not self.handle_new_requests(notified_socket):
                        continue

            self.handle_exception_sockets(exception_sockets)

    def send_message(self, client_socket, query, data):
        if data:
            packet_data = pickle.dumps(data)
            packet_query = f"{query:<{QUERYSIZE}}".encode("utf-8")
            packet_header = f"{len(packet_data):< {HEADERSIZE}}".encode("utf-8")

            packet = packet_header + packet_query + packet_data
            client_socket.send(packet)

    def receive_message(self, client_socket):
        try:
            message_header = client_socket.recv(HEADERSIZE)
            if not len(message_header):
                return False

            message_query = client_socket.recv(QUERYSIZE)
            if not len(message_query):
                return False

            message_length = int(message_header.decode("utf-8").strip())
            message_query = message_query.decode("utf-8").strip()
            return {
                "header": message_header,
                "query": message_query,
                "data": pickle.loads(client_socket.recv(message_length)),
            }

        except:
            return False

    def handle_new_connection(self):
        client_socket, client_address = self.server_socket.accept()

        incoming = self.receive_message(client_socket)
        if not incoming:
            return False

        query = incoming["query"]
        data = incoming["data"]

        if query == "REG" or query == "LOGIN":
            username = data["username"]
            password = data["password"]
            result = (
                self.attempt_registration(username, password)
                if query == "REG"
                else self.attempt_login(username, password)
            )

            token = secrets.token_hex(16) if result["success"] else 0

            auth_result = {
                "success": result["success"],
                "reason": result["reason"],
                "token": token,
            }
            self.send_message(client_socket, "AUTH", auth_result)

            if result["success"]:
                chat_color = "".join(
                    [random.choice("0123456789ABCDEF") for j in range(6)]
                )
                self.socket_list.append(client_socket)
                self.clients[client_socket] = {
                    "username": username,
                    "token": token,
                    "chat_color": chat_color,
                }
                self.new_clients.append(self.clients[client_socket].copy())
                print(
                    f"Accpeted new connection from {client_address[0]}:{client_address[1]} username:{username}"
                )
            else:
                client_socket.close()
                return False
            self.send_active_clients(client_socket)
            time.sleep(0.3)
        else:
            return False

    def handle_new_requests(self, notified_socket):
        incoming = self.receive_message(notified_socket)
        client = self.clients[notified_socket]
        # DISCONNECTION CHECK
        if not incoming:
            print(f"Closed connection from {client['username']}")
            self.socket_list.remove(notified_socket)
            self.del_clients.append(self.clients[notified_socket].copy())
            del self.clients[notified_socket]
            return False

        data = incoming["data"]
        query = incoming["query"]

        # TOKEN CHECK
        try:
            token = data["token"]
        except:
            print("Client got wrong token, throwing message...")
            return False
        if token != client["token"]:
            print("Client got wrong token, throwing message...")
            return False

        if query == "CHATUPT":
            message = data["message"]
            if len(message) > 0:
                print(f"Received message from {client['username']}: {message}")
                self.broadcast_new_messages(client, message)
            else:
                return False
        else:
            return False

    def broadcast_new_messages(self, client, message):
        for client_socket in self.clients:
            packet = {
                "username": client["username"],
                "message": message,
                "chat_color": client["chat_color"],
            }
            self.send_message(client_socket, "CHATUPT", packet)

    def broadcast_new_clients(self):
        clients_no_token = []
        for client in self.new_clients.copy():
            del client["token"]
            clients_no_token.append(client)
        for client_socket in self.clients:
            self.send_message(client_socket, "USRSNEW", clients_no_token)
        self.new_clients.clear()

    def broadcast_del_clients(self):
        clients_no_token = []
        for client in self.del_clients.copy():
            del client["token"]
            clients_no_token.append(client)
        for client_socket in self.clients:
            self.send_message(client_socket, "USRSDEL", clients_no_token)
        self.del_clients.clear()

    def send_active_clients(self, client_socket):
        clients_no_token = []
        for socket in self.clients:
            if socket is not client_socket:
                client = self.clients[socket].copy()
                del client["token"]
                clients_no_token.append(client)
        self.send_message(client_socket, "USRSNEW", clients_no_token)

    def handle_exception_sockets(self, exception_sockets):
        for notified_socket in exception_sockets:
            self.socket_list.remove(notified_socket)
            del self.clients[notified_socket]

    def attempt_login(self, username, password):
        url = (
            base_url
            + '?q={{"$and": [{{"username": "{}"}}, {{"password": "{}"}}]}}'.format(
                username, sha256(password)
            )
        )
        response = requests.request("GET", url, headers=headers)

        if len(response.text) <= 4:
            return {"success": False, "reason": "Bad username or password"}
        else:
            return {"success": True, "reason": "Access granted"}

    def attempt_registration(self, username, password):
        url = base_url + '?q={{"username": "{}"}}'.format(username)
        response = requests.request("GET", url, headers=headers)

        if len(response.text) > 4:
            return {"success": False, "reason": "Username already taken"}
        elif len(username) < 4:
            return {
                "success": False,
                "reason": "Username needs to be at least 4 characters",
            }
        elif len(password) < 6:
            return {
                "success": False,
                "reason": "Password needs to be at least 8 characters",
            }
        else:
            payload = json.dumps(
                {"username": f"{username}", "password": f"{sha256(password)}",}
            )
            requests.request("POST", base_url, data=payload, headers=headers)
            return {"success": True, "reason": "User successfully created"}


if __name__ == "__main__":
    server = Server()
    server.mgr()
    while True:
        pass
