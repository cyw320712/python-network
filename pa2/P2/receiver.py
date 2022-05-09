import struct
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import socket
from checksum import calculate_checksum
from PA2_Tools.logHandler import logHandler
from PA2_Tools.PASender import PASender

if __name__ == '__main__':
  try:
    res_filename = sys.argv[1]
    log_filename = sys.argv[2]
  except IndexError:
    print("How To Use")
    print("python receiver.py <result file name> <log file name>")
    sys.exit(1)
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.bind(('', 10090))
  sender = PASender(sock, config_file='./receiver_config.txt')

  log_handler = logHandler()
  log_handler.startLogging(log_filename)
  
  file = open(res_filename, 'wb')
  expecting_seq = 0
  print("bind success")
  src_port = 10090
  dst_port = 10091

  flag = False
  while True:
    message, addr = sock.recvfrom(4096)
    
    recv_header = message[:8]
    recv_checksum = message[6:8]
    recv_content = message[8:]

    if recv_content == b'\r\n\r\n':
      print("break pass")
      flag = True
    
    calculated = calculate_checksum(recv_header).to_bytes(2, "big")

    if calculated == recv_checksum:
      # 문제 없으면
      segment = ("ACK"+str(expecting_seq)).encode()
      packet_len = 8 + len(segment)
      header = struct.pack('!4H', src_port, dst_port, packet_len, 0)
      checksum = calculate_checksum(header)
      header = struct.pack('!4H', src_port, dst_port, packet_len, checksum)
      sender.sendto_bytes(header + segment, addr)
      log_handler.writeAck(expecting_seq, log_handler.SEND_ACK)

      if not flag:
        file.write(recv_content)
      expecting_seq = 1 - expecting_seq
    else:
      log_handler.writeAck(expecting_seq, log_handler.CORRUPTED)
      negative_seq = str(1-expecting_seq)
      sender.sendto("ACK" + negative_seq, addr)
      log_handler.writeAck(expecting_seq, log_handler.SEND_ACK_AGAIN)

    if flag:
      break
  
  sock.close()
  file.close()
  log_handler.writeEnd()