import os
from socket import *
from _thread import *
import datetime

serverPort = 10090

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('127.0.0.1', serverPort))
serverSocket.listen(10)
print('The server is ready to receive')

def replace(origin: str, target:str, dest:str):
    for i in range(0, len(origin) - len(target)):
        if origin[i:i+len(target)] == target:
            origin = origin[0:i] + dest + origin[i+len(target):]
    return origin

def find_method(data):
    if "Login" in data:
        return "LOGIN"
    elif "POST" in data:
        return "POST"
    else:
        return "GET"

def serverThread(connectionSocket, addr):
    print('Connected by: ', addr[0], ':', addr[1])

    print("outer loop")
    # while True:
        # try:
    raw = connectionSocket.recv(1024)
    if not raw:
        pass
    data = raw.decode()
    
    headers = data.split("\r\n")
    route = headers[0].split(" ")[1]
    header = "HTTP/1.0 200 OK"
    method = find_method(data)
    

    if method == "GET":
        if route == "/" or route == "/index":
            file = open('./index.html', 'r', encoding='utf-8')
            html = file.read()
            header += "\r\n\r\n"
            connectionSocket.send((header+html).encode('utf-8'))
        elif route == "/cookie":
            if "UserId=" not in data:
                header = 'HTTP/1.0 404 Not Found\r\n\r\n'
                connectionSocket.send(header.encode('utf-8'))
            else:
                userId = data.split("UserId=")[1].split(";")[0]
                start = datetime.datetime.strptime(data.split("Start_time=")[1].split("\r\n")[0], '%Y %m %d %H:%M:%S')
                header += "\r\n\r\n"
                file = open('./cookie.html', 'r', encoding='utf-8')
                html = file.read()
                parselist = html.split("&")
                cur = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y %m %d %H:%M:%S'), '%Y %m %d %H:%M:%S')
                diff = cur - start
                remain = 120 - int(diff.total_seconds())
                html = parselist[0] + userId + parselist[1] + userId + parselist[2] + str(remain) + parselist[3]
                connectionSocket.send((header+html).encode('utf-8'))
        elif route == "/storage":
            if "UserId=" not in data:
                header = 'HTTP/1.0 404 Not Found\r\n\r\n'
                connectionSocket.send(header.encode('utf-8'))
            else:
                userId = data.split("UserId=")[1].split(";")[0]
                
                for path, dirs, files in os.walk("./"+userId):
                    filelist = files
                
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
            if "UserId=" not in data:
                header = 'HTTP/1.0 404 Not Found\r\n\r\n'
                connectionSocket.send(header.encode('utf-8'))
            else:
                userId = data.split("UserId=")[1].split(";")[0]
                i = 16
                while route[i]!="/":
                    i += 1
                targetId = route[16:i]
                filename = route[i+1:]
                
                if userId != targetId:
                    connectionSocket.send("HTTP/1.0 403 Forbidden\r\n\r\n".encode('utf-8'))
                else:
                    header = "HTTP/1.0 302 Found"
                    header += "\nLocation: /storage"
                    header += "\r\n\r\n"

                    try:
                        result = replace(filename, "%20", " ")
                        os.remove('./' + userId + '/' + result)
                    except ValueError:
                        print(f"User does not have {result}")
                    except FileNotFoundError:
                        print(f"There is no such file: {result}")
                    connectionSocket.send((header).encode('utf-8'))
        elif route[0:18] == "/storage/download/":
            if "UserId=" not in data:
                header = 'HTTP/1.0 404 Not Found\r\n\r\n'
                connectionSocket.send(header.encode('utf-8'))
            else:
                userId = data.split("UserId=")[1].split(";")[0]
                i = 18
                while route[i]!="/":
                    i += 1
                targetId = route[18:i]
                filename = route[i+1:]

                if userId != targetId:
                    connectionSocket.send("HTTP/1.0 403 Forbidden\r\n\r\n".encode('utf-8'))
                else:
                    result = replace(filename, "%20", " ")
                    file_data = "404"
                    try:
                        file = open('./' + userId + '/' + result, 'rb')
                        file_data = file.read()
                        file_size = os.path.getsize('./' + userId + '/' + result)
                    except FileNotFoundError:
                        print(f"There is no such file: {result}")

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
                        connectionSocket.send((header).encode('utf-8'))
                        connectionSocket.send(file_data)
        else:
            connectionSocket.send("HTTP/1.0 404 Not Found\r\n\r\n".encode('utf-8'))
    
    elif method == "LOGIN":
        if route == "/storage":
            personal = data.split("id=")[1]
            userId = personal.split("&")[0]
            try:
                os.makedirs('./' + userId)
            except Exception:
                print("Already Participated User: Use exist data")
            file = open('./storage.html', 'r', encoding='utf-8')
            html = file.read()
            
            for path, dirs, files in os.walk("./"+userId):
                filelist = files
            parsedHtml = html[0:html.find("<ul>")] + "<ul>\n"
            for item in filelist:
                parsedHtml += '\t\t<li><div>' + item
                parsedHtml += '<a href="/storage/download/' + userId + '/'+ item + '"><button class="lm">Download</button></a>_'
                parsedHtml += '<a href="/storage/delete/' + userId + '/'+ item + '"><button>Delete</button></a>\n'
            parsedHtml += html[html.find("</ul>"):]
            header += "\nSet-Cookie: UserId=" + userId + ";Max-Age=120;"
            header += "\nSet-Cookie: Start_time=" + datetime.datetime.now().strftime('%Y %m %d %H:%M:%S') + ";Max-Age=120;"
            header += "\r\n\r\n"
            connectionSocket.send((header+parsedHtml).encode('utf-8'))
        
    elif method == "POST":
        if route == "/storage":
            if "UserId=" not in data:
                header = 'HTTP/1.0 404 Not Found\r\n\r\n'
                connectionSocket.send(header.encode('utf-8'))
            else:
                userId = data.split("UserId=")[1].split(";")[0]
                contentLength = data.split("Content-Length: ")[1].split("\r\n")[0]
                boundary = data.split("boundary=")[1].split("\r\n")[0]
                print(contentLength)
                print(boundary)

                raw_data = connectionSocket.recv(int(contentLength))
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
                uploaded = open("./"+userId+"/"+str(filename)[2:-1], "wb")
                uploaded.write(file_data)
                
                for path, dirs, files in os.walk("./"+userId):
                    filelist = files

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
    