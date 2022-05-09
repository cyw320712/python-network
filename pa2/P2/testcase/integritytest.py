import sys

file = open("result.txt", "r")
tick = 0
while True:
  content = file.readline()
  if not content: break

  if content == "integrityTest\n":
    tick += 1
  else:
    print(f"{tick} line: {content} vs 'integrityTest\n'")
    print("INTEGRITY FAIL")
    break

print("INTEGRITY SUCCESS")
file.close()