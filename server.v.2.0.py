# SERVER 13031 - 0.0.0.0
# minor changes applied
# v 2.7

import argparse
import datetime
import json
import socket
import sys
import threading
import time
from socket import socket as Socket

from src.protocol import send_data, recv_data
from src.logger import setup_logging

LOG_FILE: str = "server_debug.log"

MAX_MSG_SIZE: int = 5 * 1024 * 1024
MAX_CLIENTS: int = 30
SERVER_BACKLOG: int = 5
CLIENT_INIT_TIMEOUT: int = 300
HEARTBEAT_INTERVAL: int = 30
HEARTBEAT_PING_TIMEOUT: int = 60
CLIENT_DISCONNECT_TIMEOUT: int = 180
RELAY_DELAY: float = 0.2
RESTART_DELAY: float = 1.0

arg_parser = argparse.ArgumentParser(description="VerySecureChat Server v2.7")
arg_parser.add_argument("--config", default="server_config.json", help="Config file path")
arg_parser.add_argument("--address", help="Host address to bind")
arg_parser.add_argument("--port", type=int, help="Port to listen on")
arg_parser.add_argument("--gui", action="store_true", help="Enable GUI mode")
arg_parser.add_argument("--no-gui", action="store_true", help="Disable GUI mode")
arg_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
arg_parser.add_argument("--no-debug", action="store_true", help="Disable debug mode")
cli_args, _ = arg_parser.parse_known_args()

try:
    with open(cli_args.config, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    print(f"{cli_args.config} not found, using defaults.")
    config = {"address": "0.0.0.0", "port": 13031, "gui": False, "debug": False}

HOST_ADDR: str = cli_args.address or config.get("address", "0.0.0.0")
HOST_PORT: int = cli_args.port or config.get("port", 13031)

if cli_args.gui:
    gui_enabled = True
elif cli_args.no_gui:
    gui_enabled = False
else:
    gui_enabled = config.get("gui", False)

if cli_args.debug:
    DEBUG_MODE = True
elif cli_args.no_debug:
    DEBUG_MODE = False
else:
    DEBUG_MODE = config.get("debug", False)

logger = setup_logging("server", debug=DEBUG_MODE, log_file=LOG_FILE)

clients: dict[Socket, str] = {}
clients_last_seen: dict[Socket, float] = {}

window = None
tkDisplay = None
tkTraffic = None
btnStart = None

if gui_enabled:
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
    tk.Label(clientFrame, text="********** Connected Users **********").pack()
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
    tk.Label(trafficFrame, text="********** Traffic Log **********").pack()
    scrollBarT = tk.Scrollbar(trafficFrame)
    scrollBarT.pack(side=tk.RIGHT, fill=tk.Y)
    tkTraffic = tk.Text(trafficFrame, height=15, width=50, fg="green", bg="black")
    tkTraffic.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
    scrollBarT.config(command=tkTraffic.yview)
    tkTraffic.config(yscrollcommand=scrollBarT.set, state="disabled")
    trafficFrame.pack(side=tk.BOTTOM, pady=(5, 10))


def log_traffic(msg: str) -> None:
    logger.info("TRAFFIC: %s", msg)
    if gui_enabled and window:
        def _log() -> None:
            if tkTraffic:
                tkTraffic.config(state="normal")
                tkTraffic.insert("end", str(msg) + "\n")
                tkTraffic.see("end")
                tkTraffic.config(state="disabled")
        window.after(0, _log)


server: Socket | None = None


def start_server() -> None:
    global server
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        logger.info("Starting server v2.7 on %s %s", HOST_ADDR, HOST_PORT)
        server.bind((HOST_ADDR, HOST_PORT))
        server.listen(SERVER_BACKLOG)

        threading.Thread(target=heartbeat_loop, daemon=True).start()
        threading.Thread(target=accept_clients, args=(server,), daemon=True).start()
        if btnStart:
            btnStart.config(state="disabled")
    except Exception as e:
        logger.error("Error starting server: %s", e)
        sys.exit(1)


def stop_server() -> None:
    global server
    if btnStart:
        btnStart.config(state="normal")
    if server:
        server.close()


def restart_server() -> None:
    stop_server()
    time.sleep(RESTART_DELAY)
    start_server()


def accept_clients(the_server: Socket) -> None:
    while True:
        try:
            if len(clients) >= MAX_CLIENTS:
                try:
                    client, addr = the_server.accept()
                    client.close()
                    logger.warning("Connection rejected: max clients (%s) reached", MAX_CLIENTS)
                except Exception:
                    pass
                continue

            client, addr = the_server.accept()
            clients[client] = "Desconocido"
            threading.Thread(
                target=send_receive_client_message, args=(client, addr), daemon=True
            ).start()
        except OSError:
            break


def send_receive_client_message(client_connection: Socket, client_ip_addr: tuple) -> None:
    global clients
    client_name = ""
    client_connection.settimeout(CLIENT_INIT_TIMEOUT)

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
        logger.debug("Error receiving initial name: %s", e)
        client_connection.close()
        if client_connection in clients:
            del clients[client_connection]
            if client_connection in clients_last_seen:
                del clients_last_seen[client_connection]
        return

    update_client_names_display()

    while True:
        try:
            logger.debug("Waiting for client message...")
            raw_msg = recv_data(client_connection)
            logger.debug("Received raw_msg: %s", raw_msg is not None)
            if raw_msg is None:
                logger.debug("raw_msg is None - breaking")
                break

            data = raw_msg.decode("utf-8", errors="replace")
            clients_last_seen[client_connection] = time.time()
            if data.upper() == "/QUIT":
                logger.debug("[%s] Sent /QUIT, disconnecting...", client_name)
                break
            if data == "SYS:PONG":
                logger.debug("Heartbeat: received PONG from %s", client_name)
                continue

            client_msg = data

            logger.debug(
                "Received %d bytes from %s, preview: %s...",
                len(client_msg), client_name, client_msg[:100]
            )

            recipients = [c for c in list(clients.keys()) if c != client_connection]
            logger.debug(
                "Relaying to %d client(s), total clients: %d",
                len(recipients), len(clients)
            )

            for c in recipients:
                try:
                    send_data(c, client_msg.encode("utf-8"))
                    time.sleep(RELAY_DELAY)
                except Exception as e:
                    logger.error("Error sending to client: %s", e)

            log_traffic(
                f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Relay: {client_name} -> {len(client_msg)} bytes."
            )

            try:
                ack_msg = f"SYS:ACK:{len(client_msg)}"
                logger.debug("Sending ACK to %s: %s", client_name, ack_msg)
                send_data(client_connection, ack_msg.encode("utf-8"))
                logger.debug("ACK sent successfully")
            except Exception as e:
                logger.error("Error sending ACK to %s: %s", client_name, e)

            logger.debug("--- MESSAGE FROM %s ---\n%s\n--- END ---", client_name, client_msg)

        except Exception as e:
            logger.debug("Exception in client loop: %s", e)
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


def real_update_client_names_display(name_list: list[str]) -> None:
    if tkDisplay:
        tkDisplay.config(state="normal")
        tkDisplay.delete("1.0", "end")
        for c in name_list:
            tkDisplay.insert("end", c + "\n")
        tkDisplay.config(state="disabled")


def update_client_names_display() -> None:
    if gui_enabled and window:
        names = list(clients.values())
        window.after(0, real_update_client_names_display, names)


def heartbeat_loop() -> None:
    global clients, clients_last_seen
    while True:
        try:
            time.sleep(HEARTBEAT_INTERVAL)
            now = time.time()
            disconnected: list[Socket] = []

            for c in list(clients.keys()):
                last_seen = clients_last_seen.get(c, now)
                time_since_last_seen = now - last_seen

                if time_since_last_seen > CLIENT_DISCONNECT_TIMEOUT:
                    disconnected.append(c)
                    try:
                        c.close()
                    except Exception:
                        pass
                elif time_since_last_seen > HEARTBEAT_PING_TIMEOUT:
                    try:
                        send_data(c, b"SYS:PING")
                        logger.debug(
                            "Heartbeat: sent PING to %s", clients.get(c, "Unknown")
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

            if disconnected:
                logger.debug("Heartbeat: removed %d inactive clients", len(disconnected))

        except Exception:
            pass


def on_closing() -> None:
    logger.info("Closing server (UI)...")
    stop_server()
    if window:
        window.destroy()
    sys.exit(0)


start_server()

if gui_enabled:
    window.protocol("WM_DELETE_WINDOW", on_closing)
    window.mainloop()
else:
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Closing server (KeyboardInterrupt)...")
        stop_server()
