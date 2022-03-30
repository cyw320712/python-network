from calendar import c
import os
from socket import *
from _thread import *
import datetime

serverPort = 10090

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('127.0.0.1', serverPort))
serverSocket.listen(10)
print('The server is ready to receive')

def replace(origin, target, dest):
    for i in range(0, len(origin) - len(target)):
        if origin[i:i+len(target)] == target:
            origin = origin[0:i] + dest + origin[i+len(target):]
    return origin

def find_method(data):
    if "LOGIN" in data:
        return "LOGIN"
    if "POST" in data:
        return "POST"
    else:
        return "GET"

def send_forbidden(connectionSocket):
    header = 'HTTP/1.1 403 Forbidden'
    header += "\nContent-Length: 0"
    header += "\r\n\r\n"
    connectionSocket.send(header.encode('utf-8'))

def send_notfound(connectionSocket):
    header = 'HTTP/1.1 404 Not Found'
    header += "\nContent-Length: 0"
    header += "\r\n\r\n"
    connectionSocket.send(header.encode('utf-8'))

def serverThread(connectionSocket, addr):
    print('Connected by: ', addr[0], ':', addr[1])

    print("outer loop")
    while True:
        # try:
            data = connectionSocket.recv(2048).decode()
            # print(data)
            if not data:
                print("pass")
                connectionSocket.close()
                break

            headers = data.split("\r\n")
            route = headers[0].split(" ")[1]
            header = "HTTP/1.1 200 OK"
            method = find_method(data)
            print(method)

            if method == "GET":
                if route[0:6] == "/index":
                    if len(route) == 6:
                        file = open('./index.html', 'r', encoding='utf-8')
                        html = file.read()
                        file.close()
                        header += "\nContent-Length: " + str(len(html))
                        header += "\r\n\r\n"
                        connectionSocket.send((header+html).encode('utf-8'))
                    else:
                        personal = data.split("id=")[1]
                        userId = personal.split("&")[0]
                        try:
                            os.makedirs('./' + userId)
                        except Exception:
                            print("Already Participated User: Use exist data")
                        header = "HTTP/1.1 302 Found"
                        header += "\nContent-Length: 0"
                        header += "\nSet-Cookie: UserId=" + userId + ";Max-Age=120;"
                        header += "\nSet-Cookie: Start_time=" + datetime.datetime.now().strftime('%Y %m %d %H:%M:%S') + ";Max-Age=120;"
                        header += "\nLocation: /storage\r\n\r\n"
                        connectionSocket.send(header.encode('utf-8'))
                elif route == "/cookie":
                    if "UserId=" not in data:
                        send_forbidden(connectionSocket)
                    else:
                        userId = data.split("UserId=")[1].split(";")[0]
                        start = datetime.datetime.strptime(data.split("Start_time=")[1].split("\r\n")[0], '%Y %m %d %H:%M:%S')
                        file = open('./cookie.html', 'r', encoding='utf-8')
                        html = file.read()
                        file.close()
                        parselist = html.split("&")
                        cur = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y %m %d %H:%M:%S'), '%Y %m %d %H:%M:%S')
                        diff = cur - start
                        remain = 120 - int(diff.total_seconds())
                        html = parselist[0] + userId + parselist[1] + userId + parselist[2] + str(remain) + parselist[3]
                        header += "\nContent-Length: " + str(len(html))
                        header += "\r\n\r\n"
                        connectionSocket.send((header+html).encode('utf-8'))
                elif route == "/storage":
                    if "UserId=" not in data:
                        send_forbidden(connectionSocket)
                    else:
                        userId = data.split("UserId=")[1].split(";")[0]
                        
                        for path, dirs, files in os.walk("./"+userId):
                            filelist = files
                        
                        file = open('./storage.html', 'r', encoding='utf-8')
                        html = file.read()
                        file.close()
                        parselist = html.split("&")
                        html = parselist[0] + userId + parselist[1]

                        parsedHtml = html[0:html.find("<ul>")] + "<ul>\n"
                        for item in filelist:
                            parsedHtml += '<li><div>' + item
                            parsedHtml += '<a href="/storage/download/' + userId + '/'+ item + '"><button class="lm">Download</button></a>_'
                            parsedHtml += '<a href="/storage/delete/' + userId + '/'+ item + '"><button>Delete</button></a>\n'
                        parsedHtml += html[html.find("</ul>"):]
                        header += "\nContent-Length: " + str(len(parsedHtml))
                        header += "\r\n\r\n"
                        connectionSocket.send((header+parsedHtml).encode('utf-8'))
                elif route[0:16] == "/storage/delete/":
                    if "UserId=" not in data:
                        send_forbidden(connectionSocket)
                    else:
                        userId = data.split("UserId=")[1].split(";")[0]
                        i = 16
                        while route[i]!="/":
                            i += 1
                        targetId = route[16:i]
                        filename = route[i+1:]
                        
                        if userId != targetId:
                            send_forbidden(connectionSocket)
                        else:
                            header = "HTTP/1.1 302 Found"
                            header += "\nContent-Length: 0"
                            header += "\nLocation: /storage"
                            header += "\r\n\r\n"
                            
                            flag = "normal"
                            try:
                                result = replace(filename, "%20", " ")
                                os.remove('./' + userId + '/' + result)
                            except FileNotFoundError:
                                flag = "404"
                                print(f"There is no such file: {result}")

                            if flag == "404":
                                send_notfound(connectionSocket)
                            else:
                                connectionSocket.send((header).encode('utf-8'))
                elif route[0:18] == "/storage/download/":
                    if "UserId=" not in data:
                        send_forbidden(connectionSocket)
                    else:
                        userId = data.split("UserId=")[1].split(";")[0]
                        i = 18
                        while route[i]!="/":
                            i += 1
                        targetId = route[18:i]
                        filename = route[i+1:]

                        if userId != targetId:
                            send_forbidden(connectionSocket)
                        else:
                            result = replace(filename, "%20", " ")
                            file_data = "404"
                            try:
                                file = open('./' + userId + '/' + result, 'rb')
                                file_data = file.read()
                                file.close()
                                file_size = os.path.getsize('./' + userId + '/' + result)
                            except FileNotFoundError:
                                print(f"There is no such file: {result}")

                            if file_data == "404":
                                send_notfound(connectionSocket)
                            else:
                                header = "HTTP/1.1 200 OK"
                                header += "\nContent-Type: multipart/form-data"
                                header += "\nContent-Length: " + str(file_size)
                                header += "\nContent-Disposition: filename=" + filename
                                # header += "\nLocation: /storage"
                                header += "\r\n\r\n"
                                connectionSocket.send((header).encode('utf-8'))
                                connectionSocket.send(file_data)
                elif route[0] == "/":
                    if len(route) == 1:
                        file = open('./index.html', 'r', encoding='utf-8')
                        html = file.read()
                        file.close()
                        header += "\nContent-Length: " + str(len(html))
                        header += "\r\n\r\n"
                        connectionSocket.send((header+html).encode('utf-8'))
                    else:
                        personal = data.split("id=")[1]
                        userId = personal.split("&")[0]
                        try:
                            os.makedirs('./' + userId)
                        except Exception:
                            print("Already Participated User: Use exist data")
                        header = "HTTP/1.1 302 Found"
                        header += "\nContent-Length: 0"
                        header += "\nSet-Cookie: UserId=" + userId + ";Max-Age=120;"
                        header += "\nSet-Cookie: Start_time=" + datetime.datetime.now().strftime('%Y %m %d %H:%M:%S') + ";Max-Age=120;"
                        header += "\nLocation: /storage\r\n\r\n"
                        connectionSocket.send(header.encode('utf-8'))
                else:
                    send_forbidden(connectionSocket)
            elif method == "POST":
                if route == "/storage":
                    contentType = data.split("Content-Type: ")[1].split("\r\n")[0]
                    if contentType == "application/x-www-form-urlencoded" :
                        personal = data.split("id=")[1]
                        userId = personal.split("&")[0]
                        try:
                            os.makedirs('./' + userId)
                        except Exception:
                            print("Already Participated User: Use exist data")
                        file = open('./storage.html', 'r', encoding='utf-8')
                        html = file.read()
                        file.close()
                        parselist = html.split("&")
                        html = parselist[0] + userId + parselist[1]
                        
                        for path, dirs, files in os.walk("./"+userId):
                            filelist = files
                        parsedHtml = html[0:html.find("<ul>")] + "<ul>\n"
                        for item in filelist:
                            parsedHtml += '\t\t<li><div>' + item
                            parsedHtml += '<a href="/storage/download/' + userId + '/'+ item + '"><button class="lm">Download</button></a>_'
                            parsedHtml += '<a href="/storage/delete/' + userId + '/'+ item + '"><button>Delete</button></a>\n'
                        parsedHtml += html[html.find("</ul>"):]
                        header = "HTTP/1.1 200 OK"
                        header += "\nContent-Length: " + str(len(parsedHtml))
                        header += "\nSet-Cookie: UserId=" + userId + ";Max-Age=120;"
                        header += "\nSet-Cookie: Start_time=" + datetime.datetime.now().strftime('%Y %m %d %H:%M:%S') + ";Max-Age=120;"
                        header += "\r\n\r\n"
                        connectionSocket.send((header+parsedHtml).encode('utf-8'))
                    else:
                        if "UserId=" not in data:
                            send_forbidden(connectionSocket)
                        else:
                            userId = data.split("UserId=")[1].split(";")[0]
                            contentLength = data.split("Content-Length: ")[1].split("\r\n")[0]
                            boundary = data.split("boundary=")[1].split("\r\n")[0]
                            print(contentLength)

                            raw_data = connectionSocket.recv(2048)
                            cur = 2048
                            while cur <= int(contentLength):
                                raw_data += connectionSocket.recv(2048)
                                cur += 2048
                            print(len(raw_data))
                            i = 11
                            while str(raw_data[i-10:i]) != "b'filename=" + '"' + "'" and i < 200:
                                i += 1
                            j = i + 1
                            while str(raw_data[j:j+1]) != "b'" + '"' + "'" and j < 200:
                                j += 1
                            filename = raw_data[i:j]
                            
                            i = j + 1
                            while str(raw_data[i-4:i]) != "b'\\r\\n\\r\\n'" and i < 800:
                                i += 1
                            
                            j = i + 1
                            while str(raw_data[j:j+len(boundary)+2]) != "b'--" + boundary + "'" and j < len(raw_data):
                                j += 1
                            
                            file_data = raw_data[i:j-2]
                            print("parsing complete")
                            uploaded = open("./"+userId+"/"+str(filename)[2:-1], "wb")
                            uploaded.write(file_data)
                            uploaded.close()
                            print("write complete")
                            for path, dirs, files in os.walk("./"+userId):
                                filelist = files

                            file = open('./storage.html', 'r', encoding='utf-8')
                            html = file.read()
                            file.close()
                            parselist = html.split("&")
                            html = parselist[0] + userId + parselist[1]

                            parsedHtml = html[0:html.find("<ul>")] + "<ul>\n"
                            for item in filelist:
                                parsedHtml += '<li><div>' + item
                                parsedHtml += '<a href="/storage/download/' + userId + '/'+ item + '"><button class="lm">Download</button></a>_'
                                parsedHtml += '<a href="/storage/delete/' + userId + '/'+ item + '"><button>Delete</button></a>\n'
                            parsedHtml += html[html.find("</ul>"):]
                            header = 'HTTP/1.1 200 OK'
                            header += "\nContent-Length: " + str(len(parsedHtml))
                            header += "\r\n\r\n"
                            connectionSocket.send((header+parsedHtml).encode('utf-8'))

while True:
    connectionSocket, addr = serverSocket.accept()
    print('accepting')
    start_new_thread(serverThread, (connectionSocket, addr))
    