import os
from socket import *
from _thread import *
import datetime
import sys

serverPort = 10090

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('127.0.0.1', serverPort))
serverSocket.listen(100)
print('The server is ready to receive')
class User:
    def __init__(self, userId, userPw):
        super().__init__()
        self.userId = str(userId)
        self.userPw = userPw
        self.data = []
        for path, dirs, files in os.walk("./"+userId):
            self.data = files
    
    def replace(self, origin: str, target:str, dest:str):
        for i in range(0, len(origin) - len(target)):
            if origin[i:i+len(target)] == target:
                origin = origin[0:i] + dest + origin[i+len(target):]
        return origin

    def upload_file(self, filename):
        if filename not in self.data:
            self.data.append(filename)
            return True
        else:
            return False
    
    def delete_file(self, filename: str):
        try:
            result = self.replace(filename, "%20", " ")
            self.data.remove(result)
            os.remove('./' + self.userId + '/' + result)
        except ValueError:
            print(f"User does not have {result}")
        except FileNotFoundError:
            print(f"There is no such file: {result}")
    
    def get_file(self, filename):
        result = self.replace(filename, "%20", " ")
        if result in self.data:
            try:
                file = open('./' + self.userId + '/' + result, 'rb')
                raw_data = file.read()
                file_size = os.path.getsize('./' + self.userId + '/' + result)
                return raw_data, file_size
            except FileNotFoundError:
                print(f"There is no such file: {result}")
        else:
            print(f"There is no such file: {result}")
            return "404"
    

    def get_filelist(self):
        return self.data
    
    def get_userinfo(self):
        return self.userId

class SessionManager:
    def __init__(self):
        super().__init__()
        self.info = {}
    
    def create_session(self, csrftoken, userinfo):
        data = {}
        data["start_time"] = datetime.datetime.now()
        data["status"] = 200
        user = User(userinfo[0], userinfo[1])
        try:
            os.makedirs('./' + userinfo[0])
        except Exception:
            print("Already Participated User: Use exist data")
        data["user"] = user
        self.info[csrftoken] = data
    
    def get_user(self, csrftoken):
        return self.info[csrftoken]["user"]

    def get_expire(self, csrftoken):
        start = self.info[csrftoken]["start_time"]
        cur = datetime.datetime.now()
        diff = cur - start
        remain = 120 - int(diff.total_seconds())
        if remain <= 0 :
            return -1
        return str(remain)

    def set_expire(self, csrftoken):
        self.info[csrftoken]["status"] = 403
    
    def get_status(self, csrftoken):
        return self.info[csrftoken]["status"]

sessionManager = SessionManager()

def serverThread(connectionSocket, addr):
    print('Connected by: ', addr[0], ':', addr[1])

    raw = connectionSocket.recv(1024)
    data = raw.decode()
    
    print(data)
    headers = data.split("\r\n")
    route = headers[0].split(" ")[1]
    
    """
    Header should aftercare for containing Cookie and '\r\n\r\n'
    """
    header = "HTTP/1.0 200 OK"

    """
    Parsing CSRF TOKEN for managing cookie
    """
    csrf_pos = data.find("csrftoken=")
    csrftoken = data[csrf_pos+10:csrf_pos+74]

    """
    HTTP Method Parsing
    """
    method = ""
    if "Login" in data:
        method = "LOGIN"
    elif "POST" in data:
        method = "POST"
    else:
        method = "GET"

    if method == "GET":
        if route == "/" or route == "/index":
            file = open('./index.html', 'r', encoding='utf-8')
            html = file.read()
            header += "\r\n\r\n"
            connectionSocket.send((header+html).encode('utf-8'))
        elif route == "/cookie":
            if sessionManager.get_status(csrftoken) == 403:
                header = 'HTTP/1.0 403 Forbidden\r\n\r\n'
                connectionSocket.send(header.encode('utf-8'))
            elif sessionManager.get_expire(csrftoken) == -1:
                file = open('./index.html', 'r', encoding='utf-8')
                html = file.read()
                header += "\r\n\r\n"
                connectionSocket.send((header+html).encode('utf-8'))
                sessionManager.set_expire(csrftoken)
            else:
                userId = data.split("UserId=")[1].split("\r\n")[0]
                header += "\r\n\r\n"
                file = open('./cookie.html', 'r', encoding='utf-8')
                html = file.read()
                parselist = html.split("&")
                html = parselist[0] + userId + parselist[1] + userId + parselist[2] + sessionManager.get_expire(csrftoken) + parselist[3]
                connectionSocket.send((header+html).encode('utf-8'))
        elif route == "/storage":
            User = sessionManager.get_user(csrftoken)
            filelist = User.get_filelist()
            userId = data.split("UserId=")[1].split("\r\n")[0]
            header += "\r\n\r\n"
            file = open('./storage.html', 'r', encoding='utf-8')
            html = file.read()
            parsedHtml = html[0:html.find("<ul>")] + "<ul>\n"
            for item in filelist:
                parsedHtml += '<li><div>' + item
                parsedHtml += '<a href="/storage/download/' + userId + '/'+ item + '"><button class="lm">Download</button></a>_'
                parsedHtml += '<a href="/storage/delete/' + userId + '/'+ item + '"><button>Delete</button></a>\n'
            parsedHtml += html[html.find("</ul>"):]
            connectionSocket.send((header+parsedHtml).encode('utf-8'))
        elif route[0:16] == "/storage/delete/":
            userId = data.split("UserId=")[1].split("\r\n")[0]
            i = 16
            while route[i]!="/":
                i += 1
            targetId = route[16:i]
            filename = route[i+1:]
            print(filename)
            if userId != targetId:
                connectionSocket.send("HTTP/1.0 403 Forbidden\r\n\r\n".encode('utf-8'))
            else:
                header = "HTTP/1.0 302 Found"
                header += "\nLocation: /storage"
                header += "\r\n\r\n"
                User = sessionManager.get_user(csrftoken)
                User.delete_file(filename)
                print(header)
                connectionSocket.send((header).encode('utf-8'))
        elif route[0:18] == "/storage/download/":
            userId = data.split("UserId=")[1].split("\r\n")[0]
            i = 18
            while route[i]!="/":
                i += 1
            targetId = route[18:i]
            filename = route[i+1:]
            print(filename)
            if userId != targetId:
                connectionSocket.send("HTTP/1.0 403 Forbidden\r\n\r\n".encode('utf-8'))
            else:
                User = sessionManager.get_user(csrftoken)
                file_data, file_size = User.get_file(filename)
                if file_data == "404":
                    connectionSocket.send("HTTP/1.0 404 Not Found\r\n\r\n".encode('utf-8'))
                else:
                    header = "HTTP/1.0 200 OK"
                    header += "\nContent-Type: multipart/form-data"
                    header += "\nConnection: keep-alive"
                    header += "\nContent-Length: " + str(file_size)
                    header += "\nContent-Disposition: filename=" + filename
                    # header += "\nLocation: /storage"
                    header += "\r\n\r\n"
                    print(header)
                    connectionSocket.send((header).encode('utf-8'))
                    connectionSocket.send(file_data)
        else:
            connectionSocket.send("HTTP/1.0 404 Not Found\r\n\r\n".encode('utf-8'))
    
    elif method == "LOGIN":
        if route == "/storage":
            """
            Parse User Data
            """
            personal = data.split("id=")[1]
            userId = personal.split("&")[0]
            userPw = personal.split("pw=")[1]

            """
            Create Session for managing User Data
            """
            sessionManager.create_session(csrftoken, [userId, userPw])
            User = sessionManager.get_user(csrftoken)
            filelist = User.get_filelist()
            header += "\nSet-Cookie: UserId=" + userId + "; expires=" + (datetime.datetime.now() + datetime.timedelta(seconds=60)).strftime('%A, %d-%m-%Y %H:%M:%S GMT') + ";\r\n\r\n"
            
            file = open('./storage.html', 'r', encoding='utf-8')
            html = file.read()

            parsedHtml = html[0:html.find("<ul>")] + "<ul>\n"
            for item in filelist:
                parsedHtml += '\t\t<li><div>' + item
                parsedHtml += '<a href="/storage/download/' + userId + '/'+ item + '"><button class="lm">Download</button></a>_'
                parsedHtml += '<a href="/storage/delete/' + userId + '/'+ item + '"><button>Delete</button></a>\n'
            parsedHtml += html[html.find("</ul>"):]
            connectionSocket.send((header+parsedHtml).encode('utf-8'))
        
    elif method == "POST":
        if route == "/storage":
            userId = data.split("UserId=")[1].split("\r\n")[0]
            contentLength = data.split("Content-Length: ")[1].split("\r\n")[0]
            boundary = data.split("boundary=")[1].split("\r\n")[0]

            raw_data = connectionSocket.recv(int(contentLength))
            str_data = str(raw_data)
            bound_length = len(boundary) + 2
            i = 11
            while True:
                if str_data[i-10:i] == 'filename="':
                    # python array와 다르게 마지막 문자를 포함한다...
                    break
                else:
                    i += 1
            j = i+1
            while True:
                if str_data[j] == '"':
                    break
                else:
                    j += 1
            filename = str_data[i:j]
            while True:
                if str_data[i-8:i] == '\\r\\n\\r\\n':
                    break
                else:
                    i += 1
            j = i+1
            while True:
                if str_data[j:j+bound_length] == "--"+boundary:
                    break
                else:
                    j += 1
            file_data = raw_data[i-10:j-14]
            
            uploaded = open("./"+userId+"/"+filename, "wb")
            uploaded.write(file_data)
            sessionManager.get_user(csrftoken).upload_file(filename)
            User = sessionManager.get_user(csrftoken)
            filelist = User.get_filelist()

            header = 'HTTP/1.0 200 OK\r\n\r\n'
            file = open('./storage.html', 'r', encoding='utf-8')
            html = file.read()

            parsedHtml = html[0:html.find("<ul>")] + "<ul>\n"
            for item in filelist:
                parsedHtml += '<li><div>' + item
                parsedHtml += '<a href="/storage/download/' + userId + '/'+ item + '"><button class="lm">Download</button></a>_'
                parsedHtml += '<a href="/storage/delete/' + userId + '/'+ item + '"><button>Delete</button></a>\n'
            parsedHtml += html[html.find("</ul>"):]
            connectionSocket.send((header+parsedHtml).encode('utf-8'))

        connectionSocket.close()

while True:
    connectionSocket, addr = serverSocket.accept()
    print('accepting')
    start_new_thread(serverThread, (connectionSocket, addr))
