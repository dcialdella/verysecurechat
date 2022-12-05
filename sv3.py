# V3
import threading, socket

# Creamos una clase que manejará cada conexión individual con un cliente
class ChatServer(threading.Thread):
    def __init__(self, socket, address):
        # Inicializamos el hilo
        threading.Thread.__init__(self)

        # Asignamos el socket y la dirección del cliente
        self.sock = socket
        self.addr = address

    def run(self):
        # Recibimos un mensaje del cliente
        message = self.sock.recv(1024)

        # Imprimimos el mensaje recibido
        print(message)

        # Enviamos una respuesta al cliente
        self.sock.send("Hola, gracias por conectarte al servidor de chat")

        # Cerramos la conexión con el cliente
        self.sock.close()

# Creamos el socket del servidor
server_socket = socket.socket()

# Asignamos una dirección y puerto al socket
server_socket.bind(("localhost", 1234))

# Hacemos que el servidor escuche por nuevas conexiones
server_socket.listen()

# Bucle principal del servidor
while True:
    # Aceptamos una nueva conexión
    client_socket, client_address = server_socket.accept()

    # Creamos una nueva instancia del hilo para manejar la conexión individual con el cliente
    chat_server = ChatServer(client_socket, client_address)

    # Iniciamos el hilo
    chat_server.start()
