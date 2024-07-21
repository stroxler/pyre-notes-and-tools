import socket
import json

# Fill these out!
SOCKET_PATH = "/tmp/pyre_server_FILLME.sock"
FILE_PATH = "FILLME/absolute/path/to/some/file.py"


REQUEST = ["DisplayTypeError", [FILE_PATH]]

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(SOCKET_PATH)
r = s.makefile(mode="r")
w = s.makefile(mode="w")

message = f"{json.dumps(REQUEST)}\n"
print(f"Sending: {message}")
w.write(message)
w.flush()

raw_response = r.readline()
response = json.loads(raw_response.strip())
print(response)

