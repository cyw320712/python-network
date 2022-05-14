import struct
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from PA2_Tools.logHandler import logHandler
from checksum import calculate_checksum
from PA2_Tools.PASender import PASender
import socket

PAYLOAD_SIZE = 1016

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
  sender = PASender(sock, config_file="./config.txt")
  pos = 0
  seq = 0
  dst_port = 10090
  src_port = 10091
  flag = False
  
  print("RDT Start")
  while True:
    if pos+PAYLOAD_SIZE < file_len:
      segment = file_data[pos:pos+PAYLOAD_SIZE]
    elif pos < file_len:
      segment = file_data[pos:]
    else:
      # end 조건 다시 만들기
      segment = b"\r\n\r\n"
      flag = True
    
    pos += PAYLOAD_SIZE
    header = struct.pack('!4H', src_port, dst_port, seq, 0)
    checksum = calculate_checksum(header+segment)
    header = struct.pack('!4H', src_port, dst_port, seq, checksum)
    # header에는 src_port, dst_port, sequence number, checksum이 포함된다.

    ack = False
    first = True
    while not ack:
      ###########################################################
      # Sending Part                                            #
      ###########################################################
      sender.sendto_bytes(header + segment, (dst_addr, dst_port))
      if first:
        # 처음 보낼때는 packet은 재전송이 아니니까.
        log_handler.writePkt(seq, log_handler.SEND_DATA)
        first = False
      else:
        log_handler.writePkt(seq, log_handler.SEND_DATA_AGAIN)
      
      ###########################################################
      # Receiving Part                                          #
      ###########################################################
      message, addr = sock.recvfrom(1024)
      recv_header = message[:6]
      recv_seq = message[4:6]
      recv_checksum = message[6:8]
      recv_content = message[8:]
      ack_seq = struct.unpack('!H', recv_seq)[0]
      zero_byte = 0
      zero_byte = zero_byte.to_bytes(2, "big")

      calculated = calculate_checksum(recv_header + zero_byte + recv_content).to_bytes(2, "big")
      if calculated == recv_checksum:
        # 문제 없으면
        if str(ack_seq) == str(seq):
          ack = True
          log_handler.writePkt(seq, log_handler.SUCCESS_ACK)
        else:
          log_handler.writePkt(seq, log_handler.WRONG_SEQ_NUM)
      else:
        # 데이터가 틀리면
        log_handler.writePkt(seq, log_handler.CORRUPTED)
    
    seq = 1 - seq
    if flag:
      break

  sock.close()
  log_handler.writeEnd()
  print("RDT end")
