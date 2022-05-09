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

  flag = False
  print("RDT Start")
  while True:
    message, addr = sock.recvfrom(1024)
    
    recv_header = message[:8]
    recv_seq = message[4:6]
    recv_checksum = message[6:8]
    recv_content = message[8:]
    recv_seq = struct.unpack('!H', recv_seq)[0]

    if recv_content == b'\r\n\r\n':
      flag = True
    
    calculated = calculate_checksum(recv_header).to_bytes(2, "big")
    CORRECT = False
    if calculated == recv_checksum:
      # 문제 없으면
      if str(expecting_seq) == str(recv_seq):
        CORRECT = True
      else:
        log_handler.writeAck(expecting_seq, log_handler.WRONG_SEQ_NUM)
        CORRECT = False
    else:
      # Corrupted 됐다면
      log_handler.writeAck(expecting_seq, log_handler.CORRUPTED)
    
    if CORRECT:
      # 기다리던 sequence number가 왔으며, 문제가 없다면
      segment = ("ACK"+str(expecting_seq)).encode()
      header = struct.pack('!4H', src_port, dst_port, expecting_seq, 0)
      checksum = calculate_checksum(header)
      header = struct.pack('!4H', src_port, dst_port, expecting_seq, checksum)

      sender.sendto_bytes(header + segment, addr)
      log_handler.writeAck(expecting_seq, log_handler.SEND_ACK)

      if not flag:
        # 마지막 \r\n\r\n은 파일에 적지 않는다
        file.write(recv_content)
      
      expecting_seq = 1 - expecting_seq
    else:
      # 기다리던 sequence number가 아니거나, corrupt 됐으면
      negative_seq = 1-expecting_seq
      segment = ("ACK"+str(negative_seq)).encode()
      header = struct.pack('!4H', src_port, dst_port, negative_seq, 0)
      checksum = calculate_checksum(header)
      header = struct.pack('!4H', src_port, dst_port, negative_seq, checksum)

      sender.sendto(header + segment, addr)
      log_handler.writeAck(expecting_seq, log_handler.SEND_ACK_AGAIN)

    if flag:
      break
  
  sock.close()
  file.close()
  log_handler.writeEnd()
  print("RDT end")