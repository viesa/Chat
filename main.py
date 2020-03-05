import requests
import json
import os
import time

base_url = "https://databas-8c8d.restdb.io/rest/credentials"

headers = {
    "content-type": "application/json",
    "x-apikey": "45c1dafe70a410f56d197c98c5a88b2e8b79c",
    "cache-control": "no-cache",
}


def clear():
    os.system("clear")


while True:
    clear()
    print("(1) Login\n(2) Create\n(3) Delete\n")
    choice = input()
    if choice == "1":
        clear()
        print("Username: ")
        username = str(input())
        print("Password: ")
        password = str(input())
        url = (
            base_url
            + '?q={{"$and": [{{"username": "{}"}}, {{"password": "{}"}}]}}'.format(
                username, password
            )
        )
        response = requests.request("GET", url, headers=headers)
        if len(response.text) > 4:
            print("Logged in")
        else:
            print("Bad password")
        time.sleep(1)
    elif choice == "2":
        clear()
        print("Username: ")
        username = input()
        print("Password: ")
        password = input()
        payload = json.dumps({"username": f"{username}", "password": f"{password}"})
        response = requests.request("POST", base_url, data=payload, headers=headers)

