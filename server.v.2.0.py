# SERVER 13031 - 0.0.0.0
# minor changes applied
# v 2.0

import socket
import threading
import time
import json
import sys
import struct
import datetime

MAX_MSG_SIZE = 5 * 1024 * 1024  # Proteccion contra ataques de Memoria (5 MB MAX)

def send_data(sock, data):
    sock.sendall(struct.pack('!I', len(data)))
    sock.sendall(data)

def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet: 
            return None
        data.extend(packet)
    return bytes(data)

def recv_data(sock):
    raw_msglen = recvall(sock, 4)
    if not raw_msglen: 
        return None
    msglen = struct.unpack('!I', raw_msglen)[0]
    
    # [SECURITY PATCH] Evitar ataque de agotamiento de memoria (OOM DOS)
    if msglen > MAX_MSG_SIZE:
        print(f"[ALERTA DE SEGURIDAD] Paquete malicioso bloqueado. Tamano irreal: {msglen} bytes.")
        raise ValueError("Payload size limit exceeded")
        
    return recvall(sock, msglen)

# open file and use it as parameters.
try:
    with open('server_config.json', "r") as f:
        config = json.load(f)
except FileNotFoundError:
    print("No se encontro server_config.json, usando valores predeterminados.")
    config = {"address": "0.0.0.0", "port": 13031, "gui": False, "debug": False}

HOST_ADDR  = config.get('address', '0.0.0.0')
HOST_PORT  = config.get('port', 13031)
DEBUG_MODE = config.get('debug', False)

clients = {} # mapping from client_connection (socket) to name (str)
clients_last_seen = {}

window = None
tkDisplay = None
tkTraffic = None
btnStart = None

if config.get('gui', False):
    import tkinter as tk

    window = tk.Tk()
    window.title("Servidor Central v 2.0")

    topFrame = tk.Frame(window)
    btnStart = tk.Button(topFrame, text="RESTART", command=lambda : restart_server() )
    btnStart.pack(side=tk.LEFT)
    topFrame.pack(side=tk.TOP, pady=(5, 0))

    middleFrame = tk.Frame(window)
    lblHost = tk.Label(middleFrame, text = "Host: " + HOST_ADDR)
    lblHost.pack(side=tk.LEFT)
    lblPort = tk.Label(middleFrame, text = "Port: " + str(HOST_PORT))
    lblPort.pack(side=tk.LEFT)
    middleFrame.pack(side=tk.TOP, pady=(5, 0))

    clientFrame = tk.Frame(window)
    lblLine = tk.Label(clientFrame, text="********** Usuarios Conectados **********").pack()
    scrollBar = tk.Scrollbar(clientFrame)
    scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
    tkDisplay = tk.Text(clientFrame, height=15, width=30, fg="black")
    tkDisplay.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
    scrollBar.config(command=tkDisplay.yview)
    tkDisplay.config(yscrollcommand=scrollBar.set, background="#F4F6F7", highlightbackground="grey", state="disabled")
    clientFrame.pack(side=tk.TOP, pady=(5, 10))

    trafficFrame = tk.Frame(window)
    lblTraffic = tk.Label(trafficFrame, text="********** Registro de Trafico **********").pack()
    scrollBarT = tk.Scrollbar(trafficFrame)
    scrollBarT.pack(side=tk.RIGHT, fill=tk.Y)
    tkTraffic = tk.Text(trafficFrame, height=15, width=50, fg="green", bg="black")
    tkTraffic.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
    scrollBarT.config(command=tkTraffic.yview)
    tkTraffic.config(yscrollcommand=scrollBarT.set, state="disabled")
    trafficFrame.pack(side=tk.BOTTOM, pady=(5, 10))

def log_traffic(msg):
    if config.get('gui', False) and window:
        def _log():
            if tkTraffic:
                tkTraffic.config(state="normal")
                tkTraffic.insert("end", str(msg) + "\n")
                tkTraffic.see("end")
                tkTraffic.config(state="disabled")
        window.after(0, _log)
    elif DEBUG_MODE:
        print(msg)

server = None

def start_server():
    global server
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print('Arrancando el servidor en', HOST_ADDR, HOST_PORT)
        server.bind((HOST_ADDR, HOST_PORT))
        server.listen(5)
        
        threading.Thread(target=heartbeat_loop, daemon=True).start()
        threading.Thread(target=accept_clients, args=(server,), daemon=True).start()
        if btnStart:
            btnStart.config(state="disabled")
    except Exception as e:
        print(f'ERROR Arrancando el servidor: {e}')
        sys.exit(1)

def stop_server():
    global server
    if btnStart:
        btnStart.config(state="normal")
    if server:
        server.close()

def restart_server():
    stop_server()
    time.sleep(1)
    start_server()

def accept_clients(the_server):
    while True:
        try:
            client, addr = the_server.accept()
            clients[client] = "Desconocido"
            threading.Thread(target=send_receive_client_message, args=(client, addr), daemon=True).start()
        except OSError:
            break # server socket closed

def send_receive_client_message(client_connection, client_ip_addr):
    global clients
    client_name = ""

    try:
        raw_name = recv_data(client_connection)
        if raw_name is None:
            raise Exception("Conexion cerrada antes de recibir nombre")
        client_name = raw_name.decode('utf-8', errors='replace')
        clients[client_connection] = client_name
        clients_last_seen[client_connection] = time.time()
        welcome_msg = "Conectado. Hola " + client_name + ", escribe 'fin' o mas de 3 chars.\n\n"
        send_data(client_connection, welcome_msg.encode('utf-8'))
    except Exception as e:
        if DEBUG_MODE: 
            print("Error al recibir el nombre inicial:", e)
        client_connection.close()
        if client_connection in clients:
            del clients[client_connection]
            if client_connection in clients_last_seen: 
                del clients_last_seen[client_connection]
        return

    log_traffic(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {client_name} se conecto.")
    update_client_names_display()

    while True:
        try:
            raw_msg = recv_data(client_connection)
            if raw_msg is None:
                break
                
            data = raw_msg.decode('utf-8', errors='replace')
            clients_last_seen[client_connection] = time.time()
            if data == "fin":
                break
            if data == "SYS:PONG":
                continue

            client_msg = data

            for c in list(clients.keys()):
                if c != client_connection:
                    try:
                        send_data(c, client_msg.encode('utf-8'))
                    except Exception as e:
                        if DEBUG_MODE: 
                            print("Error enviando mensaje a cliente:", e)

            log_traffic(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Relevo: {client_name} -> {len(client_msg)} bytes.")
            if DEBUG_MODE:
                print(client_msg)

        except Exception as e:
            if DEBUG_MODE: 
                print("Cliente desconectado por error de conexion:", e)
            break

    try:
        server_msg = "CHAU!"
        send_data(client_connection, server_msg.encode('utf-8'))
    except Exception:
        pass
    
    client_connection.close()
    if client_connection in clients:
        del clients[client_connection]
        if client_connection in clients_last_seen: 
            del clients_last_seen[client_connection]

    log_traffic(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {client_name} se desconecto.")
    update_client_names_display()

def real_update_client_names_display(name_list):
    if tkDisplay:
        tkDisplay.config(state="normal")
        tkDisplay.delete('1.0', "end")
        for c in name_list:
            tkDisplay.insert("end", c+"\n")
        tkDisplay.config(state="disabled")

def update_client_names_display():
    if config.get('gui', False) and window:
        names = list(clients.values())
        window.after(0, real_update_client_names_display, names)

def heartbeat_loop():
    while True:
        time.sleep(30)
        now = time.time()
        for c in list(clients.keys()):
            last_seen = clients_last_seen.get(c, now)
            if now - last_seen > 60:
                try: 
                    c.close()
                except Exception: 
                    pass
            else:
                try: 
                    send_data(c, b"SYS:PING")
                except Exception: 
                    pass

def on_closing():
    print("\nCerrando servidor (UI)...")
    stop_server()
    if window:
        window.destroy()
    sys.exit(0)

start_server()

if config.get('gui', False):
    window.protocol("WM_DELETE_WINDOW", on_closing)
    window.mainloop()
else:
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCerrando servidor (KeyboardInterrupt)...")
        stop_server()
