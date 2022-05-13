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
  print("bind success")
  sender = PASender(sock, config_file='./receiver_config.txt')

  log_handler = logHandler()
  log_handler.startLogging(log_filename)
  
  file = open(res_filename, 'wb')
  expecting_seq = 0
  src_port = 10090
  dst_port = 10091
  window_size = 0
  sequence_size = 0
  packet_len = 9999
  pos = 0
  window = []
  print("RDT Start")
  while pos < packet_len:
    message, addr = sock.recvfrom(1024)

    recv_header = struct.unpack('!6H', message[:12])
    src_port = recv_header[0]
    dst_port = recv_header[1]
    recv_seq = recv_header[2]
    window_size = recv_header[3]
    packet_len = recv_header[4]
    recv_checksum = recv_header[5]
    recv_header = struct.pack('!6H', src_port, dst_port, recv_seq, window_size, packet_len, 0)
    recv_content = message[12:]

    calculated = calculate_checksum(recv_header + recv_content)
    STATUS = 0
    if calculated == recv_checksum:
      # 문제 없으면
      if window_size == 0:
        window_size = 0
      if sequence_size == 0:
        sequence_size = window_size * 2 + 1
      if len(window) != packet_len:
        for _ in range(packet_len):
          window.append(0)
      if expecting_seq == recv_seq:
        STATUS = 1
      else:
        log_handler.writeAck(recv_seq, log_handler.WRONG_SEQ_NUM)
    else:
      # Corrupted 됐다면
      log_handler.writeAck(expecting_seq, log_handler.CORRUPTED)
    
    if STATUS:
      # 기다리던 sequence number가 왔으며, 문제가 없다면
      segment = ("ACK").encode()
      header = struct.pack('!5H', src_port, dst_port, expecting_seq, STATUS, 0)
      checksum = calculate_checksum(header+segment)
      header = struct.pack('!5H', src_port, dst_port, expecting_seq, STATUS, checksum)

      sender.sendto_bytes(header + segment, addr)
      if window[pos] == 0:
        window[pos] = 1
        log_handler.writeAck(expecting_seq, log_handler.SEND_ACK)
        file.write(recv_content)
        pos+=1
      else:
        log_handler.writeAck(expecting_seq, log_handler.SEND_ACK_AGAIN)
      expecting_seq += 1
      expecting_seq %= sequence_size
    else:
      # 기다리던 sequence number가 아니거나, corrupt 됐으면
      if expecting_seq == 0:
        negative_seq = 11
      else:
        negative_seq = expecting_seq -1
      segment = ("ACK").encode()
      header = struct.pack('!5H', src_port, dst_port, negative_seq, STATUS, 0)
      checksum = calculate_checksum(header+segment)
      header = struct.pack('!5H', src_port, dst_port, negative_seq, STATUS, checksum)

      sender.sendto(header + segment, addr)
      log_handler.writeAck(negative_seq, log_handler.SEND_ACK_AGAIN)
    
  
  sock.close()
  file.close()
  log_handler.writeEnd()
  print("RDT end")