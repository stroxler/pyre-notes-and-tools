import sys 
import re

codes = []

for line in sys.stdin.readlines():
    line = line.strip()
    if len(line) == 9 and re.match("D[0-9]{8}", line):
        codes.append(line)


print(' '.join(codes))
