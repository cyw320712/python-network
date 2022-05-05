import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from PA2_Tools.logHandler import logHandler
from PA2_Tools.PASender import PASender
import socket

if __name__ == '__main__':
  try:
    dst_addr = sys.argv[1]
    window_size = int(sys.argv[2])
    src_filename = sys.argv[3]
    log_filename = sys.argv[4]
  except IndexError:
    print("How To Uses")
    print("python sender.py <receiver's IP address> <window size> <source file name> <log file name>")
    sys.exit(1)

  log_handler = logHandler()
  log_handler.startLogging(log_filename)
  try:
    file = open(src_filename, 'rb')
  except Exception:
    print("file not found")
    sys.exit(1)

  file_data = file.read()
  file.close()

  send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sender = PASender(send_sock, loss_rate=0, corrupt_rate=0)
  log_handler.writePkt(0, log_handler.SEND_DATA)
  sender.sendto(file_data, (dst_addr, 10090))
  send_sock.close()
  log_handler.writeEnd()
