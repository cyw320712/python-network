import sys

file = open("text.txt", "w")
content = "integrityTest\n"*20000

file.write(content)
file.close()