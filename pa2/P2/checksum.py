import struct

def calculate_checksum(header):
  length = len(header)
  checksum = 0

  # To avoid out of range error, length should be even
  if length % 2 != 0:
    length += 1
    header += struct.pack('!B', 0)
  
  for i in range(0, length, 2):
    checksum += (header[i + 1]) << 8 + header[i]

  checksum = (checksum >> 16) + (checksum & 0xffff)
  checksum += (checksum >> 16)

  checksum = ~checksum & 0xffff
  return checksum