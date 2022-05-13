import struct
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import socket
from checksum import calculate_checksum
from PA2_Tools.logHandler import logHandler
from PA2_Tools.PASender import PASender

if __name__ == '__main__':
  # 사용자 입력 파라미터 받아오기
  try:
    res_filename = sys.argv[1]
    log_filename = sys.argv[2]
  except IndexError:
    print("How To Use")
    print("python receiver.py <result file name> <log file name>")
    sys.exit(1)
  
  # Socket 및 PASender 초기화
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.bind(('', 10090))
  print("bind success")
  sender = PASender(sock, config_file='./receiver_config.txt')

  # Log handler init
  log_handler = logHandler()
  log_handler.startLogging(log_filename)
  
  # 파일 및 각종 변수 초기화
  file = open(res_filename, 'wb')
  expecting_seq = 0
  src_port = 10090
  dst_port = 10091
  sequence_size = 0
  packet_len = 9999
  pos = 0
  window = []

  # RDT를 위한 통신 Loop
  print("RDT Start")
  while pos < packet_len:
    message, addr = sock.recvfrom(1024)

    # 헤더 파싱해서 각각 저장 후 checksum 계산을 위해 다시 Pack
    recv_header = struct.unpack('!6H', message[:12])
    src_port = recv_header[0]
    dst_port = recv_header[1]
    recv_seq = recv_header[2]
    window_size = recv_header[3]
    packet_len = recv_header[4]
    recv_checksum = recv_header[5]
    recv_header = struct.pack('!6H', src_port, dst_port, recv_seq, window_size, packet_len, 0)
    recv_content = message[12:]

    # Checksum 계산
    calculated = calculate_checksum(recv_header + recv_content)
    
    # 받은 소켓의 상태를 분류하기 위한 STATUS 변수
    STATUS = 0

    if calculated == recv_checksum:
      # 문제 없으면

      # Sequence number 범위 설정
      if sequence_size == 0:
        sequence_size = window_size * 2 + 1
      
      # Window가 초기화되지 않은 상태라면 초기화
      if len(window) != packet_len:
        for _ in range(packet_len):
          window.append(0)
      
      # State 분류 
      if expecting_seq == recv_seq:
        # 기대하던 sequence num을 받았다면
        STATUS = 1
      else:
        # 기대하던 sequence num가 아니라면
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
      # 한 번도 보낸 적 없는 ACK이라면
      if window[pos] == 0:
        window[pos] = 1
        log_handler.writeAck(expecting_seq, log_handler.SEND_ACK)
        file.write(recv_content)
        pos+=1
      # 보낸적 있는 ACK이라면
      else:
        log_handler.writeAck(expecting_seq, log_handler.SEND_ACK_AGAIN)
      
      # Expecting_seq 업데이트
      expecting_seq += 1
      expecting_seq %= sequence_size
    else:
      # 기다리던 sequence number가 아니거나, corrupt 됐으면
      if expecting_seq == 0 and sequence_size == 0:
        # 첫 번째 PACKET에서 loss가 발생했다면 아무 수나 보내기
        negative_seq = 1111
      elif expecting_seq == 0:
        # 그게 아닌 0번 loss에 대해서는 마지막 sequence number 보내기
        negative_seq = sequence_size -1
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