import sys
import socket

try:
  res_filename = sys.argv[1]
  log_filename = sys.argv[2]
except IndexError:
  print("How To Use")
  print("python receiver.py <result file name> <log file name>")
  sys.exit(1)
recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind(('127.0.0.1', 10090))

try:
  file = open(res_filename, 'wb')
except Exception:
  print("file not found")
  sys.exit(1)

message, addr = recv_sock.recvfrom(1)
file.write(message)
file.close()