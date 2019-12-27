import select, socket, sys, queue

class Server():
    def __init__(self, host='192.168.1.13', port=8080, recv_buffer=4096):
        self.host = host
        self.port = port
        self.recv_buffer = recv_buffer
        # Sockets from which we expect to read
        self.inputs = []
        # Sockets to which we expect to write
        self.outputs = []
        # Outgoing message queues (socket:Queue)
        self.message_queues = {}

    def bind(self):
        try:
            # Create a TCP/IP socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setblocking(0) # non blocking socket
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)

            # add server socket object to the list of readable connections
            self.inputs.append(self.server_socket)

            print("Chat server listenning on port: {}, host: {}".format(self.port, self.host))

        except socket.error as error:
            print(error)
            print("Couldn't connect to the remote host: {}".format(self.host))
            sys.exit(1)

    # broadcast chat messages to all connected clients exept the socket in arg
    def broadcast(self, sock, data):
        for s in self.inputs:
            # send the message only to peer
            if not (s is self.server_socket) and not (s is sock):
                # Add output channel for response
                if s not in self.outputs:
                    self.outputs.append(s)

                self.message_queues[s].put(data)

    def run(self):
        self.bind()

        while self.inputs:
            readable, writable, exceptional = select.select(self.inputs, self.outputs, self.inputs)

            for s in readable:
                if s is self.server_socket:
                    # A "readable" server socket is ready to accept a connection
                    connection, client_address = self.server_socket.accept()
                    connection.setblocking(0) # non blocking socket
                    self.inputs.append(connection)

                    self.message_queues[connection] = queue.Queue()

                    print('Client (%s, %s) connected' % client_address)
                # a message from a client on a new connection
                else:
                    try:

                        data = s.recv(self.recv_buffer)

                        if data:
                            # A readable client socket has data
                            print('Received "%s" from %s' % (data, s.getpeername()))

                            self.broadcast(s, data)
                        else:
                            # Interpret empty result as closed connection
                            print('Closing', client_address, 'after reading no data')

                            # Stop listening for input on the connection
                            if s in self.outputs:
                                self.outputs.remove(s)
                            self.inputs.remove(s)
                            s.close()

                            # Remove message queue
                            del self.message_queues[s]
                    except:
                        continue

            for s in writable:
                try:
                    next_msg = self.message_queues[s].get_nowait()
                except queue.Empty:
                    print('Output queue for', s.getpeername(), 'is empty')
                    self.outputs.remove(s)
                else:
                    try:
                        print('Sending "%s" to %s' % (next_msg, s.getpeername()))
                        s.send(next_msg)
                    except:
                        s.close()



            for s in exceptional:
                print('Handling exceptional condition for', s.getpeername())

                self.inputs.remove(s)
                if s in self.outputs:
                    self.outputs.remove(s)
                s.close()

                # Remove message queue
                del self.message_queues[s]

if __name__ == "__main__":
    server = Server()
    server.run()
