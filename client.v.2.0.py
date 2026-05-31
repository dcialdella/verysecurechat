# Client define server ip / port 13031
# v 2.7
# Fix for Windows O.S.
# Thanks ZeroCool22 for Debugging.
# Thanks IGNIZ for Lot of changes
#
import argparse
import datetime
import json
import logging
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from typing import Any

from src.crypto import (
    create_gpg,
    decrypt_message,
    encrypt_message,
    get_valid_sorted_keys,
    list_private_keys,
    list_public_keys,
)
from src.logger import setup_logging
from src.protocol import recv_data, send_data

CLIENT_TIMEOUT: int = 180
TIMEOUT_CHECK_INTERVAL_MS: int = 30000
SEND_DELAY: float = 0.2

arg_parser = argparse.ArgumentParser(description="VerySecureChat Client v2.7")
arg_parser.add_argument("--config", default="client_config.json", help="Config file path")
arg_parser.add_argument("--server", help="Server address")
arg_parser.add_argument("--port", type=int, help="Server port")
arg_parser.add_argument("--gpgid", help="GPG identity UID to use")
arg_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
arg_parser.add_argument("--no-debug", action="store_true", help="Disable debug mode")
cli_args, _ = arg_parser.parse_known_args()

logger = setup_logging("client")

try:
    with open(cli_args.config, "r") as configFile:
        config: dict[str, Any] = json.load(configFile)
except FileNotFoundError:
    logger.warning("%s not found, client will close.", cli_args.config)
    sys.exit("No config file. Please create client_config.json.")

client: socket.socket | None = None
key_map: dict[int, dict[str, Any]] = {}
valid_public_keys: list[dict[str, Any]] = []
valid_private_keys: list[dict[str, Any]] = []
last_activity: float | None = None
selected_public_key: dict[str, Any] | None = None

HOST_ADDR: str = cli_args.server or config.get("server", "")
HOST_PORT: int = cli_args.port or config.get("port", 13031)

debug_mode: bool
if cli_args.debug:
    debug_mode = True
elif cli_args.no_debug:
    debug_mode = False
else:
    debug_mode = config.get("debug", False)

if debug_mode:
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.DEBUG)
    logging.getLogger().setLevel(logging.DEBUG)

if not HOST_ADDR or not HOST_PORT:
    sys.exit("No server IP or PORT in configuration.")

try:
    gpg = create_gpg()
    public_keys = list_public_keys(gpg)
    private_keys = list_private_keys(gpg)
    if debug_mode:
        logger.debug("Private keys found:")
        for key in private_keys:
            logger.debug("  Key ID: %s, UID: %s", key["keyid"], key.get("uids", []))
except Exception as e:
    logger.critical("GPG not installed or in PATH: %s", e)
    sys.exit("Please install GPG on your system (e.g., brew install gnupg)")

valid_public_keys = get_valid_sorted_keys(gpg, private=False)
valid_private_keys = get_valid_sorted_keys(gpg, private=True)

window = tk.Tk()
window.title("Cliente v 2.7 (VerySecureChat)")
username: str = " "

BG_COLOR: str = "#1a1b26"
FG_COLOR: str = "#c0caf5"
ACCENT: str = "#7aa2f7"
BTN_BG: str = "#3d59a1"
window.configure(bg=BG_COLOR)

style = ttk.Style()
try:
    style.theme_use("clam")
except Exception:
    pass
style.configure("TFrame", background=BG_COLOR)
style.configure(
    "TLabel", background=BG_COLOR, foreground=FG_COLOR, font=("Helvetica", 12)
)
style.configure(
    "TButton",
    background=BTN_BG,
    foreground="white",
    font=("Helvetica", 11, "bold"),
    padding=3,
)
style.map("TButton", background=[("active", ACCENT)])

topFrame = ttk.Frame(window)
ttk.Label(topFrame, text="GPG U.ID:").pack(side=tk.LEFT, padx=5)
entNameText = tk.StringVar()
entName = ttk.Combobox(topFrame, width=50, textvariable=entNameText)
entName.pack(side=tk.LEFT, padx=5)

keyNames = (
    [key["uids"][0] for key in valid_private_keys]
    if valid_private_keys
    else ["<No Private GPG Key>"]
)
entName["values"] = keyNames
if keyNames:
    cli_gpgid = cli_args.gpgid
    saved_gpgid = config.get("GPGid", "")
    if cli_gpgid:
        entNameText.set(cli_gpgid)
    elif saved_gpgid and saved_gpgid in keyNames:
        entNameText.set(saved_gpgid)
    else:
        entNameText.set(keyNames[0])

btnConnect = ttk.Button(topFrame, text="Connect", command=lambda: connect())
btnConnect.pack(side=tk.LEFT, padx=5)
btnDisconnect = ttk.Button(
    topFrame, text="Disconnect", command=lambda: handle_disconnection()
)
btnDisconnect.state(["disabled"])
btnDisconnect.pack(side=tk.LEFT, padx=5)
btnReload = ttk.Button(
    topFrame, text="🔄 Recargar Llaves", command=lambda: reload_keys()
)
btnReload.pack(side=tk.LEFT, padx=5)

lblStatus = tk.Label(
    topFrame, text="● Desconectado", fg="#f7768e", bg=BG_COLOR, font=("Helvetica", 10)
)
lblStatus.pack(side=tk.LEFT, padx=10)
topFrame.pack(side=tk.TOP, pady=15)

displayFrame = ttk.Frame(window)
scrollBar = tk.Scrollbar(displayFrame)
scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
tkDisplay = tk.Text(
    displayFrame,
    height=25,
    width=65,
    bg="#24283b",
    fg=FG_COLOR,
    font=("Helvetica", 12),
    insertbackground=FG_COLOR,
    highlightthickness=0,
    borderwidth=1,
)
tkDisplay.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0))
tkDisplay.tag_config("tag_your_message", foreground="#9ece6a")
tkDisplay.tag_config("tag_your_message2", foreground="#7aa2f7")
scrollBar.config(command=tkDisplay.yview)
tkDisplay.config(yscrollcommand=scrollBar.set, state="disabled")
displayFrame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10)

bottomFrame = ttk.Frame(window)
ttk.Label(bottomFrame, text="Message:").pack(side=tk.LEFT, padx=5)
tkMessage = tk.Text(
    bottomFrame,
    height=4,
    width=70,
    bg="#24283b",
    fg=FG_COLOR,
    font=("Helvetica", 12),
    insertbackground=FG_COLOR,
    highlightthickness=0,
    borderwidth=1,
)
tkMessage.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5), pady=(10, 15))
tkMessage.config(state="disabled")
tkMessage.bind(
    "<Return>", (lambda event: (getChatMessage(tkMessage.get("1.0", tk.END)), "break"))
)
bottomFrame.pack(side=tk.BOTTOM, fill=tk.X)

tkUserList = tk.Listbox(
    displayFrame,
    height=25,
    width=50,
    exportselection=False,
    bg="#24283b",
    fg=FG_COLOR,
    selectbackground=ACCENT,
    selectforeground="#000000",
    highlightthickness=0,
    font=("Helvetica", 12),
)
tkUserList.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
key_map = {}
tkUserList.insert(0, "<SELECT RECIPIENT>")
for i, key in enumerate(valid_public_keys, start=1):
    val = key["uids"][0] if key.get("uids") else "Unknown ID"
    tkUserList.insert(i, val)
    key_map[i] = key
tkUserList.select_set(0)


def set_status(text: str, color: str) -> None:
    lblStatus.config(text=text, fg=color)


def reload_keys() -> None:
    global public_keys, private_keys, valid_public_keys, valid_private_keys, key_map
    try:
        public_keys = list_public_keys(gpg)
        private_keys = list_private_keys(gpg)
        valid_public_keys = get_valid_sorted_keys(gpg, private=False)
        valid_private_keys = get_valid_sorted_keys(gpg, private=True)

        tkUserList.delete(0, tk.END)
        key_map = {}
        tkUserList.insert(0, "<SELECT RECIPIENT>")
        for i, key in enumerate(valid_public_keys, start=1):
            val = key["uids"][0] if key.get("uids") else "Unknown ID"
            tkUserList.insert(i, val)
            key_map[i] = key
        tkUserList.select_set(0)
        logger.debug("GPG keys reloaded.")
    except Exception as e:
        messagebox.showerror("ERROR!!!", f"Failed to reload GPG: {e}")


def connect() -> None:
    global username, client, selected_public_key, config
    if not valid_private_keys:
        messagebox.showerror(
            "ERROR!!!", "No tienes claves privadas GPG validas para usar el chat."
        )
        return

    if len(entName.get()) < 1:
        messagebox.showerror("ERROR!!!", "You must provide your GPG ID.")
        return

    selections = tkUserList.curselection()
    if not selections or selections[0] == 0:
        messagebox.showwarning(
            "Invalid Recipient",
            "You must select a public key from the list to encrypt messages.\nSelect a contact.",
        )
        return

    selected_public_key = key_map.get(selections[0])
    if not selected_public_key:
        messagebox.showerror("ERROR", "Invalid public key selected.")
        return

    username = entName.get()

    saved_gpgid = config.get("GPGid", "")
    if username != saved_gpgid:
        config["GPGid"] = username
        with open(cli_args.config, "w") as configFile:
            json.dump(config, configFile, indent=2)

    connect_to_server(username)


def connect_to_server(name: str) -> None:
    global client, last_activity
    try:
        set_status("● Conectando...", "#e0af68")
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        client.settimeout(None)
        client.connect((HOST_ADDR, HOST_PORT))
        send_data(client, name.encode("utf-8"))

        last_activity = time.time()
        start_client_timeout_check()

        entName.config(state="disabled")
        btnConnect.state(["disabled"])
        btnDisconnect.state(["!disabled"])
        tkMessage.config(state="normal")
        tkUserList.config(state="disabled")
        tkMessage.focus_set()

        set_status("● Conectado", "#9ece6a")

        threading.Thread(
            target=receive_message_from_server, args=(client,), daemon=True
        ).start()
    except Exception as e:
        set_status("● Desconectado", "#f7768e")
        messagebox.showerror(
            "ERROR!!!", f"Error connecting to server {HOST_ADDR}:{HOST_PORT}.\n{e}"
        )


def handle_disconnection() -> None:
    global client, selected_public_key
    selected_public_key = None
    if client:
        try:
            client.close()
        except Exception:
            pass
        client = None
    entName.config(state="normal")
    btnConnect.state(["!disabled"])
    try:
        btnDisconnect.state(["disabled"])
    except Exception:
        pass
    tkMessage.config(state="disabled")
    tkUserList.select_set(0)
    tkUserList.config(state="normal")
    set_status("● Desconectado", "#f7768e")


def start_client_timeout_check() -> None:
    window.after(TIMEOUT_CHECK_INTERVAL_MS, check_client_timeout)


def check_client_timeout() -> None:
    global last_activity, client
    if client is not None and last_activity is not None:
        if time.time() - last_activity > CLIENT_TIMEOUT:
            logger.debug("Client timeout: disconnecting due to inactivity")
            handle_disconnection()
        else:
            start_client_timeout_check()


def insert_text_safe(text: str, tag: str | None = None) -> None:
    def _insert() -> None:
        tkDisplay.config(state="normal")
        if tag:
            tkDisplay.insert(tk.END, text, tag)
        else:
            tkDisplay.insert(tk.END, text)
        tkDisplay.config(state="disabled")
        tkDisplay.see(tk.END)

    window.after(0, _insert)


def receive_message_from_server(sck: socket.socket) -> None:
    global last_activity
    while True:
        try:
            raw = recv_data(sck)
            if raw is None:
                break
            from_server = raw.decode("utf-8", errors="replace")
        except Exception:
            break

        if from_server == "SYS:PING":
            last_activity = time.time()
            try:
                send_data(sck, b"SYS:PONG")
            except Exception:
                pass
            continue

        if from_server.startswith("SYS:ACK:"):
            logger.debug("Message acknowledged by server: %s", from_server)
            continue

        last_activity = time.time()

        cuando = datetime.datetime.now()

        if "-----BEGIN PGP" in from_server:
            logger.debug("Received encrypted:\n%s...", from_server[:100])
            try:
                encrypted_bytes = from_server.encode("utf-8")

                decrypted_data = decrypt_message(gpg, encrypted_bytes)

                if not decrypted_data.ok:
                    decrypted_data = decrypt_message(
                        gpg, encrypted_bytes, extra_args=["--try-all-secrets"]
                    )

                logger.debug(
                    "decrypt ok=%s, status=%s",
                    decrypted_data.ok, decrypted_data.status
                )

                if decrypted_data.ok:
                    data = decrypted_data.data
                    if isinstance(data, bytes):
                        data = data.decode("utf-8", errors="replace")
                    logger.debug("decrypted: %s", data)
                    insert_text_safe(
                        f"IN: {cuando} - {data}\n",
                        "tag_your_message2",
                    )
                else:
                    insert_text_safe(
                        f"IN: {cuando} - [DECRYPT FAILED: {decrypted_data.status}]\n",
                        "tag_your_message2",
                    )
            except Exception as e:
                logger.debug("Decrypt exception: %s", e)
                insert_text_safe(
                    f"IN: {cuando} - [DECRYPT ERROR: {e}]\n", "tag_your_message2"
                )
        else:
            insert_text_safe(f"IN: {cuando} - {from_server}", "tag_your_message2")

    try:
        sck.close()
    except Exception:
        pass
    window.after(0, handle_disconnection)


def getChatMessage(msg: str) -> None:
    global last_activity
    msg = msg.strip()
    if not msg:
        return
    last_activity = time.time()
    cuando = datetime.datetime.now()

    insert_text_safe(f"OUT-{cuando} - {msg}\n", "tag_your_message")
    send_msg_to_server(msg)

    tkMessage.delete("1.0", tk.END)


def send_msg_to_server(msg: str) -> None:
    global client
    client_msg = str(msg)

    if client_msg.upper() == "/QUIT":
        window.destroy()
        sys.exit(0)

    if len(client_msg) > 0:
        if selected_public_key is None:
            messagebox.showwarning(
                "No Recipient", "Please reconnect and select a public key."
            )
            return
        destKeys = [selected_public_key]

        for key in destKeys:
            recipient = key["uids"][0] if key.get("uids") else ""
            recipient_keyid = key.get("keyid", "unknown")
            recipient_fingerprint = key.get("fingerprint", "")
            cuando = datetime.datetime.now()

            logger.debug(
                "Encrypting to recipient=%s, keyid=%s, fingerprint=%s",
                recipient, recipient_keyid, recipient_fingerprint
            )

            encrypt_key = recipient_fingerprint or recipient_keyid
            try:
                encrypted_data = encrypt_message(gpg, client_msg, encrypt_key)
                if not encrypted_data.ok:
                    logger.debug("SEND: %s. OK: False (Key for %s unusable)", cuando, recipient)
                    continue

                encrypted_string = str(encrypted_data)
                logger.debug("SEND: %s. OK: True", cuando)
                logger.debug("Sent encrypted:\n%s\n--- END ---", encrypted_string)
                send_data(client, encrypted_string.encode("utf-8"))
                time.sleep(SEND_DELAY)
            except Exception as e:
                insert_text_safe(
                    f"Error sending to {recipient}: {e}\n", "tag_your_message2"
                )


window.update_idletasks()
w = window.winfo_width()
h = window.winfo_height()
x = (window.winfo_screenwidth() // 2) - (w // 2)
y = (window.winfo_screenheight() // 2) - (h // 2)
window.geometry(f"+{x}+{y}")
window.minsize(w, h)

window.mainloop()
