# SERVER 13031 - 0.0.0.0
# minor changes applied
# v 1.40

# import tkinter as tk  NOT NEEDED if no GUI
import socket
import threading
import time
import json 

# open file and use it as parameters.
config = json.load( open ('server_config.json', "r")  ) 

HOST_ADDR  = config['address']
HOST_PORT  = config['port']
DEBUG_MODE = config['debug']

if config['address'] == '':
   HOST_ADDR = '127.0.0.1'

if config['port'] == '':
   PORT = '13031'

client_name = " "
clients = []
clients_names = []

if (config['gui']):

    # Load library ONLY if needed by GUI interface
    import tkinter as tk

    window = tk.Tk()
    window.title("Sevidor Central v 1.40")

    # Top frame consisting of two buttons widgets (i.e. btnStart, btnStop)
    topFrame = tk.Frame(window)
    btnStart = tk.Button(topFrame, text="RESTART", command=lambda : restart_server() )
    btnStart.pack(side=tk.LEFT)
    # btnStop = tk.Button(topFrame, text="Desconectado", command=lambda : stop_server(), state=tk.DISABLED)
    # btnStop.pack(side=tk.LEFT)
    topFrame.pack(side=tk.TOP, pady=(5, 0))

    # Middle frame consisting of two labels for displaying the host and port info
    middleFrame = tk.Frame(window)
    lblHost = tk.Label(middleFrame, text = "Host: X.X.X.X")
    lblHost.pack(side=tk.LEFT)
    lblPort = tk.Label(middleFrame, text = "Port: XXXX")
    lblPort.pack(side=tk.LEFT)
    middleFrame.pack(side=tk.TOP, pady=(5, 0))

    # The client frame shows the client area
    clientFrame = tk.Frame(window)
    lblLine = tk.Label(clientFrame, text="********** Usuarios Conectados **********").pack()
    scrollBar = tk.Scrollbar(clientFrame)
    scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
    tkDisplay = tk.Text(clientFrame, height=15, width=30, fg="black")
    tkDisplay.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
    scrollBar.config(command=tkDisplay.yview)
    tkDisplay.config(yscrollcommand=scrollBar.set, background="#F4F6F7", highlightbackground="grey", state="disabled")
    clientFrame.pack(side=tk.BOTTOM, pady=(5, 10))


# Start server function
def start_server():

    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print( 'Arrancando el servidor.')
        print(socket.AF_INET)
        print(socket.SOCK_STREAM)

        server.bind((HOST_ADDR, HOST_PORT))
        server.listen(5)  # server is listening for client connection

        threading._start_new_thread(accept_clients, (server, " "))
        if (config['gui']):
            lblHost["text"] = "Host: " + HOST_ADDR
            lblPort["text"] = "Port: " + str(HOST_PORT)
    except:
        print( 'ERROR Arrancando el servidor, reintente en 30 segs.')
        quit()


# Stop server function
def stop_server():
    global server
    btnStart.config(state=tk.NORMAL)
#    btnStop.config(state=tk.DISABLED)

def restart_server():
    stop_server
    time.sleep(1)
    restart_server
    time.sleep(1)

def accept_clients(the_server, y):
    while True:
        client, addr = the_server.accept()
        clients.append(client)

        # use a thread so as not to clog the gui thread
        threading._start_new_thread(send_receive_client_message, (client, addr))


# Function to receive message from current client AND
# Send that message to other clients
def send_receive_client_message(client_connection, client_ip_addr):
    global server, client_name, clients, clients_addr
    client_msg = " "

    # send welcome message to client
    try:
        client_name  = client_connection.recv(4096).decode()
        welcome_msg = "Conectado. Hola " + client_name + ", escribe 'fin' o mas de 3 chars.\n\n"
        client_connection.send(welcome_msg.encode())
    except:
        data = ""

    clients_names.append(client_name)

    update_client_names_display(clients_names)  # update client names display

    while True:
        try:
            data = client_connection.recv(4096).decode()
        except:
            data = ""

        if not data: break
        if data == "fin": break

        client_msg = data

        idx = get_client_index(clients, client_connection)
        sending_client_name = clients_names[idx]

        for c in clients:
            if c != client_connection:
#                server_msg = str(sending_client_name + "->" + client_msg)
                try:
                    server_msg = str(client_msg)
                    c.send(server_msg.encode())
                except:
                    server_msg = ""

                if ( DEBUG_MODE ) :
                    print ( server_msg )

    # find the client index then remove from both lists(client name list and connection list)
    idx = get_client_index(clients, client_connection)
    del clients_names[idx]
    del clients[idx]
    server_msg = "CHAU!"
    client_connection.send(server_msg.encode())
    client_connection.close()

    update_client_names_display(clients_names)  # update client names display

# Return the index of the current client in the list of clients
def get_client_index(client_list, curr_client):
    idx = 0
    for conn in client_list:
        if conn == curr_client:
            break
        idx = idx + 1

    return idx

# Update client name display when a new client connects OR
# When a connected client disconnects
def update_client_names_display(name_list):
    if (config['gui']):
        tkDisplay.config(state=tk.NORMAL)
        tkDisplay.delete('1.0', tk.END)

        for c in name_list:
            tkDisplay.insert(tk.END, c+"\n")
        tkDisplay.config(state=tk.DISABLED)

start_server()

if (config['gui']):
    window.mainloop()
else:

#
# EOF
#

