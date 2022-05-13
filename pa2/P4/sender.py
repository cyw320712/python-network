import struct
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from PA2_Tools.logHandler import logHandler
from checksum import calculate_checksum
from PA2_Tools.PASender import PASender
import socket

PAYLOAD_SIZE = 1012
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.01)
src_port = 10091
log_handler = logHandler()
packet_list = []
window = []

# pos 번째 packet만 전송
def sendPacket(sender, pos, packet_len, dst, window_size):
  # print(f"====sender====\n{window}")
  dst_addr = dst[0]
  dst_port = dst[1]
  sequence_size = window_size * 2 + 1
  seq = pos % sequence_size
  if pos < packet_len:
    segment = packet_list[pos]
  else:
    return
  
  header = struct.pack('!6H', src_port, dst_port, seq, window_size, packet_len, 0)
  checksum = calculate_checksum(header+segment)
  header = struct.pack('!6H', src_port, dst_port, seq, window_size, packet_len, checksum)
  
  sender.sendto_bytes(header + segment, (dst_addr, dst_port))
  if window[pos] == -1:
    window[pos] = 0
    log_handler.writePkt(seq, log_handler.SEND_DATA)
  else:
    window[pos] = 0
    log_handler.writePkt(seq, log_handler.SEND_DATA_AGAIN)


if __name__ == '__main__':
  # 사용자 입력 파라미터 받아오기
  try:
    dst_addr = sys.argv[1]
    window_size = int(sys.argv[2])
    src_filename = sys.argv[3]
    log_filename = sys.argv[4]
  except IndexError:
    print("How To Uses")
    print("python sender.py <receiver's IP address> <window size> <source file name> <log file name>")
    sys.exit(1)

  # Packet 개수를 정하는 과정
  file_size = os.path.getsize(src_filename)
  packet_len = file_size // PAYLOAD_SIZE + 1

  # Target 파일 찾아서 열기
  try:
    file = open(src_filename, 'rb')
  except Exception:
    print("file not found")
    sys.exit(1)

  # file data를 나눠 packet data로 저장
  file_data = file.read(PAYLOAD_SIZE)
  while file_data:
    packet_list.append(file_data)
    file_data = file.read(PAYLOAD_SIZE)
    window.append(-1)
  file.close()

  # Sender 및 각종 변수 초기화
  sender = PASender(sock, config_file="./config.txt")
  log_handler.startLogging(log_filename)
  dst_port = 10090
  pos = 0
  flag = False
  sequence_size = window_size * 2 + 1
  processed = -1
  
  # RDT를 위한 통신 Loop
  print("RDT Start")
  while not flag:
    #########################################
    #                Send Pkt               #
    #########################################
    cur_window = pos
    for i in range(cur_window, cur_window+window_size):
      sendPacket(sender, i, packet_len, (dst_addr, 10090), window_size)
    
    #########################################
    #                Recv ACK               #
    #########################################
    cnt = 0
    first = True
    flag = False
    pos = cur_window
    while True:
      expecting_seq = (pos + cnt) % sequence_size

      if cur_window >= packet_len:
        # 현재 윈도우가 마지막 Packet에 도달했다면, 모든 패킷을 제대로 보냈다는 뜻
        # 떄문에 종료조건 set 후 break
        flag = True
        break
      try:
        message, addr = sock.recvfrom(1024)
        first = False
      except TimeoutError:
        # 이번 윈도우의 마지막 packet에 대한 recv 요청에서 timeout이 뜬다면
        break
      
      # 헤더 파싱해서 각각 저장 후 checksum 계산을 위해 다시 Pack
      recv_header =  struct.unpack('!5H', message[:10])
      src_port = recv_header[0]
      dst_port = recv_header[1]
      recv_seq = recv_header[2]
      recv_status = recv_header[3]
      recv_checksum = recv_header[4]
      recv_header = struct.pack('!5H', src_port, dst_port, recv_seq, recv_status, 0)
      recv_content = message[10:]

      # Checksum 계산
      calculated = calculate_checksum(recv_header + recv_content)

      if calculated == recv_checksum:
        # 데이터에 corrupt가 발생하지 않으면
        if recv_status:
          # ReACK이 아니라면
          if recv_seq == expecting_seq:
            # Sender가 보낸 packet에도 corrupt가 발생하지 않아
            # Sequence number가 정상적인 경우
            # corrupt가 발생해도 recv_status는 0이 되기 때문에
            # 여기에 들어오면 무조건 같다!
            window[pos+cnt] = 1
            log_handler.writePkt(expecting_seq, log_handler.SUCCESS_ACK)
            if pos + cnt + window_size < packet_len:
              window[pos+cnt+window_size] = -1
            sendPacket(sender, pos+cnt+window_size, packet_len, (dst_addr, 10090), window_size)
            cur_window += 1
            # print(f"window up: {cur_window}")
        else:
          # ReACK이라면
          if processed == recv_seq:
            cnt += 1
            continue
          elif recv_seq != expecting_seq:
            # ReACK이면서 expecting_Seq이면? wrong seq num이지만
            # timeout에 의한 wrong seq num일 수 있기 때문에 구분 할 수 없다
            # 때문에 로그는 남기지 않고, 중복처리를 방지하기 위한 장치만 추가
            log_handler.writeTimeout(expecting_seq)
            processed = recv_seq
            continue
      else:
        # 데이터에 corrupt가 발생하면
        log_handler.writePkt(expecting_seq, log_handler.CORRUPTED)
        break
      
      # 받으려고 시도한 횟수 +1
      cnt += 1
    
    # ACK된 연속된 패킷으로 윈도우 옮기기
    pos = cur_window

  # RDT Loop에서 나온 후 socket, logger 종료 파트
  sock.close()
  log_handler.writeEnd()
  print("RDT end")
