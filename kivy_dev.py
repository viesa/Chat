import socket
import time
import threading
import random

from chat_client import Client

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.animation import Animation
from kivy.uix.button import Button
from kivy.uix.label import Label


kv = Builder.load_file("my.kv")


IP = "localhost"
PORT = 1234


def writeToStatus(status, message, onComplete=None):
    status.opacity = 0
    status.text = message
    fadeIn = Animation(opacity=1, duration=0.1)
    stayVisible = Animation(duration=1.7)
    fadeOut = Animation(opacity=0, duration=0.1)
    if onComplete:
        fadeOut.on_complete = onComplete
    full = fadeIn + stayVisible + fadeOut
    full.start(status)


def disableW(w):
    w.disabled = True
    return


def enableW(w):
    w.disabled = False
    return


class LoginWindow(Screen):
    def __init__(self, client, sm, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.sm = sm

    def authenticateLogin(self):
        widgets = [self.username, self.password, self.loginButton, self.registerButton]
        for widget in widgets:
            disableW(widget)

        if not self.try_login():
            writeToStatus(self.loginStatus, "Failed to connect to server")
        else:
            while not self.client.new_status:
                pass
            writeToStatus(self.loginStatus, self.client.status)
            self.client.status = ""
            self.client.new_status = False

            if len(self.client.token) > 1:
                self.sm.current = "win_chat"

        for widget in widgets:
            enableW(widget)

    def authenticateRegister(self):
        widgets = [self.username, self.password, self.loginButton, self.registerButton]
        for widget in widgets:
            disableW(widget)

        if not self.try_register():
            writeToStatus(self.loginStatus, "Failed to connect to server")
        else:
            while not self.client.new_status:
                pass
            writeToStatus(self.loginStatus, self.client.status)
            self.client.status = ""
            self.client.new_status = False

        for widget in widgets:
            enableW(widget)

    def try_login(self):
        if self.client.init_connection():
            credentials = {
                "username": self.username.text,
                "password": self.password.text,
            }
            self.client.add_send("LOGIN", credentials)
            return True
        else:
            return False

    def try_register(self):
        if self.client.init_connection():
            credentials = {
                "username": self.username.text,
                "password": self.password.text,
            }
            self.client.add_send("REG", credentials)
            return True
        else:
            return False


class ChatWindow(Screen):
    def __init__(self, client, sm, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.sm = sm
        self.is_active = True
        self.worker = threading.Thread(target=self.chat_mgr)
        self.chat_history.text = "\n"
        self.active_clients = []

    def on_enter(self):
        self.worker.start()

    def send_message(self):
        message = {"message": self.chat_input.text, "token": self.client.token}
        self.client.add_send("CHATUPT", message)
        self.chat_input.text = ""
        pass

    def chat_mgr(self):
        while self.is_active:
            once = False
            for new_msg in self.client.new_messages:
                self.chat_history.text += (
                    f"<[color={new_msg['chat_color']}]"
                    + new_msg["username"]
                    + "[color=FFFFFF]> "
                    + new_msg["message"]
                    + "\n"
                )
                once = True
            if once:
                self.client.new_messages.clear()
                self.update_chat_history_layout()

            once = False
            for new_client in self.client.new_clients:
                self.active_clients.append(new_client)
                once = True
            for del_client in self.client.del_clients:
                self.active_clients.remove(del_client)
                once = True

            self.client.new_clients.clear()
            self.client.del_clients.clear()

            if once:
                self.active_clients_label.text = "\n"
                for active_client in self.active_clients:
                    self.active_clients_label.text += (
                        f"<[color={active_client['chat_color']}]"
                        + active_client["username"]
                        + "[color=FFFFFF]>"
                        + "\n"
                    )
                self.update_active_clients_layout()

            time.sleep(0.1)

    def update_chat_history_layout(self):
        self.chat_history_layout.height = self.chat_history.texture_size[1] + 15
        self.chat_history.height = self.chat_history.texture_size[1]
        self.chat_history.text_size = (
            self.chat_history.width * 0.98,
            None,
        )

    def update_active_clients_layout(self):
        self.active_clients_layout.height = (
            self.active_clients_label.texture_size[1] + 15
        )
        self.active_clients_label.height = self.active_clients_label.texture_size[1]
        self.active_clients_label.text_size = (
            self.active_clients_label.width * 0.98,
            None,
        )


class WindowManager(ScreenManager):
    pass


class MyMainApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = Client()
        self.sm = ScreenManager(transition=FadeTransition())
        self.win_login = LoginWindow(self.client, self.sm)
        self.win_chat = ChatWindow(self.client, self.sm)
        self.sm.add_widget(self.win_login)
        self.sm.add_widget(self.win_chat)

    def build(self):
        return self.sm

    def on_stop(self):
        self.client.is_active = False
        self.client.client_socket.close()
        self.client.worker.join()
        if self.sm.current == "win_chat":
            self.win_chat.is_active = False
            self.win_chat.worker.join()


if __name__ == "__main__":
    MyMainApp().run()

