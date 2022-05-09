import struct
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from PA2_Tools.logHandler import logHandler
from checksum import calculate_checksum
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
  file_len = len(file_data)
  file.close()
  
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sender = PASender(sock, loss_rate=0, corrupt_rate=0)
  pos = 0
  seq = 0
  dst_port = 10090
  src_port = 10091

  while pos <= file_len:
    if pos < file_len:
      segment = file_data[pos:pos+window_size]
    else:
      segment = b"\r\n\r\n"
    pos += window_size
    packet_len = 8 + len(segment)
    header = struct.pack('!4H', src_port, dst_port, packet_len, 0)
    checksum = calculate_checksum(header)
    header = struct.pack('!4H', src_port, dst_port, packet_len, checksum)

    ack = False
    first = True
    while not ack:
      sender.sendto_bytes(header + segment, (dst_addr, dst_port))
      if first:
        log_handler.writePkt(seq, log_handler.SEND_DATA)
        first = False
      else:
        log_handler.writePkt(seq, log_handler.SEND_DATA_AGAIN)
      
      message, addr = sock.recvfrom(4096)
      
      recv_header = message[:8]
      recv_checksum = message[6:8]
      recv_content = message[8:]

      calculated = calculate_checksum(recv_header).to_bytes(2, "big")
      if calculated == recv_checksum:
        # 문제 없으면
        ack_seq = str(recv_content[3:])[2]
        if str(ack_seq) == str(seq):
          ack = True
          log_handler.writePkt(seq, log_handler.SUCCESS_ACK)
        else:
          log_handler.writePkt(seq, log_handler.WRONG_SEQ_NUM)
      else:
        # 데이터가 틀리면
        log_handler.writePkt(seq, log_handler.CORRUPTED)
        
    
    seq = 1 - seq

  sock.close()
  log_handler.writeEnd()
