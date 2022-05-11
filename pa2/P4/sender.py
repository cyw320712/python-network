import struct
import sys, os
import time
import threading
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

def sendPacket(sender, pos, packet_len, dst, window_size):
  dst_addr = dst[0]
  dst_port = dst[1]
  cnt = 0
  fin = 0
  # print(pos)
  while cnt < window_size:
    seq = (pos+cnt) % window_size
    if pos + cnt < packet_len:
      segment = packet_list[pos+cnt]
    else:
      break
    
    header = struct.pack('!6H', src_port, dst_port, seq, window_size, fin, 0)
    checksum = calculate_checksum(header+segment)
    header = struct.pack('!6H', src_port, dst_port, seq, window_size, fin, checksum)
    # header에는 src_port, dst_port, sequence number, checksum이 포함된다.
    # print(checksum)
    sender.sendto_bytes(header + segment, (dst_addr, dst_port))
    if window[pos+cnt] == -1:
      window[pos+cnt] = 0
      log_handler.writePkt(seq, log_handler.SEND_DATA)
    else:
      window[pos+cnt] = 0
      log_handler.writePkt(seq, log_handler.SEND_DATA_AGAIN)
    
    cnt += 1


def recvPacket(start, packet_len, window_size):
  sock.settimeout(0.01)
  cnt = 0
  first = True
  flag = False
  while cnt < window_size:
    expecting_seq = (start + cnt) % window_size
    if (start + cnt) >= packet_len:
      flag = True
      break
    if first:
      try:
        message, addr = sock.recvfrom(1024)
      except TimeoutError:
        cnt += 1
        # Timeout 된다면 log만 남기고 무시
        log_handler.writeTimeout(expecting_seq)
        break
    else:
      try:
        message, addr = sock.recvfrom(1024)
      except TimeoutError:
        cnt += 1
        # 첫 패킷에 대한 Timeout제외는 모두 무시
        continue
    
    recv_header = message[:6]
    recv_seq = message[4:6]
    recv_content = message[8:]
    recv_checksum = message[6:8]
    
    ack_seq = struct.unpack('!H', recv_seq)[0]
    zero_byte = 0
    zero_byte = zero_byte.to_bytes(2, "big")

    calculated = calculate_checksum(recv_header + zero_byte + recv_content).to_bytes(2, "big")
    if calculated == recv_checksum:
      # 문제 없으면
      if str(ack_seq) == str(expecting_seq):
        window[start+cnt] = 1
        print(f"window up: {start+cnt}")
        log_handler.writePkt(expecting_seq, log_handler.SUCCESS_ACK)
      else:
        log_handler.writePkt(expecting_seq, log_handler.WRONG_SEQ_NUM)
    else:
      # 데이터가 틀리면
      log_handler.writePkt(expecting_seq, log_handler.CORRUPTED)
    cnt += 1
  
  return flag

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

  dst_port = 10090
  log_handler.startLogging(log_filename)
  try:
    file = open(src_filename, 'rb')
  except Exception:
    print("file not found")
    sys.exit(1)
  # sock.bind((dst_addr, dst_port))

  file_data = file.read(PAYLOAD_SIZE)
  file_size = os.path.getsize(src_filename)
  packet_len = file_size // PAYLOAD_SIZE + 1

  while file_data:
    packet_list.append(file_data)
    file_data = file.read(PAYLOAD_SIZE)
    window.append(-1)
  file.close()

  sender = PASender(sock, config_file="./config.txt")
  print("RDT Start")
  
  pos = 0
  flag = False
  while not flag:
    sendPacket(sender, pos, packet_len, (dst_addr, 10090), window_size)
    flag = recvPacket(pos, packet_len, window_size)
    # print(window)
    shift = 0
    while pos + shift < packet_len and window[pos+shift] == 1:
      shift += 1
    pos += shift

  segment = b''
  fin = 1
  header = struct.pack('!6H', src_port, dst_port, 0, window_size, fin, 0)
  checksum = calculate_checksum(header+segment)
  header = struct.pack('!6H', src_port, dst_port, 0, window_size, fin, checksum)
  sender.sendto_bytes(header + segment, (dst_addr, dst_port))

  sock.close()
  log_handler.writeEnd()
  print("RDT end")
