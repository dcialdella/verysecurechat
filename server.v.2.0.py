# SERVER 13031 - 0.0.0.0
# minor changes applied
# v 2.7

import socket
import threading
import time
import json
import sys
import struct
import datetime

MAX_MSG_SIZE = 5 * 1024 * 1024  # Proteccion contra ataques de Memoria (5 MB MAX)
MAX_CLIENTS = 30  # Maximo clientes conectados


def send_data(sock, data):
    sock.sendall(struct.pack("!I", len(data)))
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
    msglen = struct.unpack("!I", raw_msglen)[0]

    # [SECURITY PATCH] Evitar ataque de agotamiento de memoria (OOM DOS)
    if msglen > MAX_MSG_SIZE:
        print(
            f"[ALERTA DE SEGURIDAD] Paquete malicioso bloqueado. Tamano irreal: {msglen} bytes."
        )
        raise ValueError("Payload size limit exceeded")

    return recvall(sock, msglen)


# open file and use it as parameters.
try:
    with open("server_config.json", "r") as f:
        config = json.load(f)
except FileNotFoundError:
    print("server_config.json not found, using defaults.")
    config = {"address": "0.0.0.0", "port": 13031, "gui": False, "debug": False}

HOST_ADDR = config.get("address", "0.0.0.0")
HOST_PORT = config.get("port", 13031)
DEBUG_MODE = config.get("debug", False)

clients = {}  # mapping from client_connection (socket) to name (str)
clients_last_seen = {}

window = None
tkDisplay = None
tkTraffic = None
btnStart = None

if config.get("gui", False):
    import tkinter as tk

    window = tk.Tk()
    window.title("Servidor Central v 2.7")

    topFrame = tk.Frame(window)
    btnStart = tk.Button(topFrame, text="RESTART", command=lambda: restart_server())
    btnStart.pack(side=tk.LEFT)
    topFrame.pack(side=tk.TOP, pady=(5, 0))

    middleFrame = tk.Frame(window)
    lblHost = tk.Label(middleFrame, text="Host: " + HOST_ADDR)
    lblHost.pack(side=tk.LEFT)
    lblPort = tk.Label(middleFrame, text="Port: " + str(HOST_PORT))
    lblPort.pack(side=tk.LEFT)
    middleFrame.pack(side=tk.TOP, pady=(5, 0))

    clientFrame = tk.Frame(window)
    lblLine = tk.Label(clientFrame, text="********** Connected Users **********").pack()
    scrollBar = tk.Scrollbar(clientFrame)
    scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
    tkDisplay = tk.Text(clientFrame, height=15, width=30, fg="black")
    tkDisplay.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
    scrollBar.config(command=tkDisplay.yview)
    tkDisplay.config(
        yscrollcommand=scrollBar.set,
        background="#F4F6F7",
        highlightbackground="grey",
        state="disabled",
    )
    clientFrame.pack(side=tk.TOP, pady=(5, 10))

    trafficFrame = tk.Frame(window)
    lblTraffic = tk.Label(trafficFrame, text="********** Traffic Log **********").pack()
    scrollBarT = tk.Scrollbar(trafficFrame)
    scrollBarT.pack(side=tk.RIGHT, fill=tk.Y)
    tkTraffic = tk.Text(trafficFrame, height=15, width=50, fg="green", bg="black")
    tkTraffic.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
    scrollBarT.config(command=tkTraffic.yview)
    tkTraffic.config(yscrollcommand=scrollBarT.set, state="disabled")
    trafficFrame.pack(side=tk.BOTTOM, pady=(5, 10))


def log_traffic(msg):
    if config.get("gui", False) and window:

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
        print("Starting server v2.7 on", HOST_ADDR, HOST_PORT)
        server.bind((HOST_ADDR, HOST_PORT))
        server.listen(5)

        threading.Thread(target=heartbeat_loop, daemon=True).start()
        threading.Thread(target=accept_clients, args=(server,), daemon=True).start()
        if btnStart:
            btnStart.config(state="disabled")
    except Exception as e:
        print(f"ERROR starting server: {e}")
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
            if len(clients) >= MAX_CLIENTS:
                try:
                    client, addr = the_server.accept()
                    client.close()
                    if DEBUG_MODE:
                        print(
                            f"Connection rejected: max clients ({MAX_CLIENTS}) reached"
                        )
                except Exception:
                    pass
                continue

            client, addr = the_server.accept()
            clients[client] = "Desconocido"
            threading.Thread(
                target=send_receive_client_message, args=(client, addr), daemon=True
            ).start()
        except OSError:
            break  # server socket closed


def send_receive_client_message(client_connection, client_ip_addr):
    global clients
    client_name = ""
    client_connection.settimeout(300)

    try:
        raw_name = recv_data(client_connection)
        if raw_name is None:
            raise Exception("Connection closed before receiving name")
        client_name = raw_name.decode("utf-8", errors="replace")
        clients[client_connection] = client_name
        clients_last_seen[client_connection] = time.time()
        welcome_msg = (
            "Connected. Hello " + client_name + ", type '/quit' to disconnect.\n\n"
        )
        send_data(client_connection, welcome_msg.encode("utf-8"))
        log_traffic(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {client_name} connected. (Clients: {len(clients)})"
        )
    except Exception as e:
        if DEBUG_MODE:
            print("Error al recibir el nombre inicial:", e)
        client_connection.close()
        if client_connection in clients:
            del clients[client_connection]
            if client_connection in clients_last_seen:
                del clients_last_seen[client_connection]
        return

    update_client_names_display()

    while True:
        try:
            raw_msg = recv_data(client_connection)
            if raw_msg is None:
                break

            data = raw_msg.decode("utf-8", errors="replace")
            clients_last_seen[client_connection] = time.time()
            if data.upper() == "/QUIT":
                break
            if data == "SYS:PONG":
                if DEBUG_MODE:
                    print(f"Heartbeat: received PONG from {client_name}")
                continue

            client_msg = data

            recipients = [c for c in list(clients.keys()) if c != client_connection]
            print(
                f"DEBUG: Relaying to {len(recipients)} client(s), total clients: {len(clients)}"
            )

            for c in recipients:
                try:
                    send_data(c, client_msg.encode("utf-8"))
                    time.sleep(0.2)
                except Exception as e:
                    print(f"ERROR sending to client: {e}")

            log_traffic(
                f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Relay: {client_name} -> {len(client_msg)} bytes."
            )
            if DEBUG_MODE:
                print(f"--- MENSAJE DE {client_name} ---\n{client_msg}\n--- FIN ---")

        except Exception as e:
            if DEBUG_MODE:
                print("Cliente desconectado por error de conexion:", e)
            break

    try:
        server_msg = "BYE!"
        send_data(client_connection, server_msg.encode("utf-8"))
    except Exception:
        pass

    client_connection.close()
    if client_connection in clients:
        del clients[client_connection]
        if client_connection in clients_last_seen:
            del clients_last_seen[client_connection]

    log_traffic(
        f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {client_name} disconnected. (Clients: {len(clients)})"
    )
    update_client_names_display()


def real_update_client_names_display(name_list):
    if tkDisplay:
        tkDisplay.config(state="normal")
        tkDisplay.delete("1.0", "end")
        for c in name_list:
            tkDisplay.insert("end", c + "\n")
        tkDisplay.config(state="disabled")


def update_client_names_display():
    if config.get("gui", False) and window:
        names = list(clients.values())
        window.after(0, real_update_client_names_display, names)


def heartbeat_loop():
    global clients, clients_last_seen
    while True:
        try:
            time.sleep(30)
            now = time.time()
            disconnected = []

            for c in list(clients.keys()):
                last_seen = clients_last_seen.get(c, now)
                time_since_last_seen = now - last_seen

                if time_since_last_seen > 180:
                    disconnected.append(c)
                    try:
                        c.close()
                    except Exception:
                        pass
                elif time_since_last_seen > 60:
                    try:
                        send_data(c, b"SYS:PING")
                        if DEBUG_MODE:
                            print(
                                f"Heartbeat: sent PING to {clients.get(c, 'Unknown')}"
                            )
                    except Exception:
                        disconnected.append(c)
                        try:
                            c.close()
                        except Exception:
                            pass

            for c in disconnected:
                name = clients.get(c, "Unknown")
                if c in clients:
                    del clients[c]
                if c in clients_last_seen:
                    del clients_last_seen[c]
                log_traffic(
                    f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {name} disconnected (timeout). (Clients: {len(clients)})"
                )

            if disconnected and DEBUG_MODE:
                print(f"Heartbeat: removed {len(disconnected)} inactive clients")

        except Exception:
            pass


def on_closing():
    print("\nClosing server (UI)...")
    stop_server()
    if window:
        window.destroy()
    sys.exit(0)


start_server()

if config.get("gui", False):
    window.protocol("WM_DELETE_WINDOW", on_closing)
    window.mainloop()
else:
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nClosing server (KeyboardInterrupt)...")
        stop_server()
