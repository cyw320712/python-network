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

  print("RDT Start")
  while True:
    message, addr = sock.recvfrom(1048)
    
    recv_header = struct.unpack('!6H', message[:12])
    src_port = recv_header[0]
    dst_port = recv_header[1]
    recv_seq = recv_header[2]
    window_size = recv_header[3]
    recv_isFin = recv_header[4]
    recv_checksum = recv_header[5]
    recv_header = struct.pack('!6H', src_port, dst_port, recv_seq, window_size, recv_isFin, 0)
    recv_content = message[12:]
    if recv_isFin == 1:
      break

    calculated = calculate_checksum(recv_header + recv_content)
    STATUS = 0
    if calculated == recv_checksum:
      # 문제 없으면
      if expecting_seq == recv_seq:
        STATUS = 1
      else:
        log_handler.writeAck(recv_seq, log_handler.WRONG_SEQ_NUM)
        STATUS = 0
    else:
      # Corrupted 됐다면
      log_handler.writeAck(expecting_seq, log_handler.CORRUPTED)
    
    if STATUS:
      # 기다리던 sequence number가 왔으며, 문제가 없다면
      segment = ("ACK"+str(expecting_seq)).encode()
      header = struct.pack('!5H', src_port, dst_port, expecting_seq, STATUS, 0)
      checksum = calculate_checksum(header+segment)
      header = struct.pack('!5H', src_port, dst_port, expecting_seq, STATUS, checksum)

      sender.sendto_bytes(header + segment, addr)
      log_handler.writeAck(expecting_seq, log_handler.SEND_ACK)

      file.write(recv_content)
      expecting_seq += 1
      expecting_seq %= window_size
    else:
      # 기다리던 sequence number가 아니거나, corrupt 됐으면
      segment = ("ACK"+str(expecting_seq)).encode()
      header = struct.pack('!5H', src_port, dst_port, expecting_seq, STATUS, 0)
      checksum = calculate_checksum(header+segment)
      header = struct.pack('!5H', src_port, dst_port, expecting_seq, STATUS, checksum)

      sender.sendto(header + segment, addr)
      log_handler.writeAck(expecting_seq, log_handler.SEND_ACK_AGAIN)
      
  
  sock.close()
  file.close()
  log_handler.writeEnd()
  print("RDT end")