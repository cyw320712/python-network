import os
from socket import *
from _thread import *
import datetime

serverPort = 10090

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('127.0.0.1', serverPort))
serverSocket.listen(1)
print('The server is ready to receive')

class User:
    def __init__(self, Id, Pw):
        self.userId = Id
        self.userPw = Pw
        self.data = []
        super().__init__()
    
    def upload_file(self, filename):
        self.data.append(filename)
    
    def get_filelist(self):
        return self.data
    
    def get_userinfo(self):
        return self.userId


class CookieManager:
    def __init__(self):
        self.info = {}
        super().__init__()
    
    def create_cookie(self, csrftoken, userinfo):
        data = {}
        data["start_time"] = datetime.datetime.now()
        data["status"] = 200
        user = User(userinfo[0], userinfo[1])
        try:
            os.makedirs('./' + userinfo[0])
        except Exception:
            print("Use alraedy created folder")
        data["user"] = user
        self.info[csrftoken] = data
    
    def get_user(self, csrftoken):
        return self.info[csrftoken]["user"]

    def get_expire(self, csrftoken):
        start = self.info[csrftoken]["start_time"]
        cur = datetime.datetime.now()
        diff = cur - start
        remain = 60 - int(diff.total_seconds())
        if remain <= 0 :
            self.info[csrftoken]["status"] = 400
            return -1
        return remain

cookieManager = CookieManager()

def serverThread(connectionSocket, addr):
    print('Connected by: ', addr[0], ':', addr[1])
    while True:
        data = connectionSocket.recv(1024).decode()
        print(data)
        headers = data.split("\r\n")
        filename = headers[0].split(" ")[1]
        
        """
        Parsing CSRF TOKEN for managing cookie
        """
        csrf_pos = data.find("csrftoken=")
        csrftoken = data[csrf_pos+10:csrf_pos+74]

        method = ""
        if "PUT" in data:
            method = "PUT"
        elif "POST" in data:
            method = "POST"
        elif "DELETE" in data:
            method = "DELETE"
        else:
            method = "GET"
        
        print(method)
        print(filename)

        if method == "GET":
            header = 'HTTP/1.0 200 OK\r\n\r\n'
            if filename == "/":
                file = open('./index.html', 'r', encoding='utf-8')
                html = file.read()
            elif filename == "/cookie":
                if cookieManager.get_expire(csrftoken) == -1:
                    file = open('./index.html', 'r', encoding='utf-8')
                    html = file.read()
                else:
                    file = open('.'+filename+'.html', 'r', encoding='utf-8')
                    html = file.read()
                    parselist = html.split("&")
                    html = parselist[0] + cookieManager.get_user(csrftoken).get_userinfo() + parselist[1] + cookieManager.get_user(csrftoken) + parselist[2] + str(cookieManager.get_expire(csrftoken)) + parselist[3]
            elif filename == "/storage":
                if cookieManager.get_expire(csrftoken) == -1:
                    file = open('./index.html', 'r', encoding='utf-8')
                    html = file.read()
                else:
                    User = cookieManager.get_user(csrftoken)
                    filelist = User.get_filelist()
                    file = open('.'+filename+'.html', 'r', encoding='utf-8')
                    html = file.read()
                    parselist = html.split("&")
            else:
                file = open('.'+filename+'.html', 'r', encoding='utf-8')
                html = file.read()
            connectionSocket.send((header+html).encode('utf-8'))
        
        elif method == "POST":
            if filename == "/index":
                personal = data.split("id=")[1]
                userId = personal.split("&")[0]
                userPw = personal.split("pw=")[1]

                header = 'HTTP/1.0 200 OK\r\n\r\n'
                file = open('.'+filename+'.html', 'r', encoding='utf-8')
                cookieManager.create_cookie(csrftoken, [userId, userPw])
                html = file.read()
            if filename == "/storage":
                print(data)
                file = open('.'+filename+'.html', 'r', encoding='utf-8')
                html = file.read()
                connectionSocket.send((header+html).encode('utf-8'))
            else:
                connectionSocket.send((header+html).encode('utf-8'))

        connectionSocket.close()
        break

while True:
    connectionSocket, addr = serverSocket.accept()
    print('accepting')
    start_new_thread(serverThread, (connectionSocket, addr))

serverSocket.close()

