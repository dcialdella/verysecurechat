# Client define server ip / port 13031
# v 2.7
# Fix for Windows O.S.
# Thanks ZeroCool22 for Debugging.
# Thanks IGNIZ for Lot of changes
#
import sys
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import socket
import threading
import datetime
import json
import gnupg
import struct
import time
import platform

TCP_KEEPIDLE = 0x10 if platform.system() == "Darwin" else 16
TCP_KEEPINTVL = 0x11 if platform.system() == "Darwin" else 18
TCP_KEEPCNT = 0x12 if platform.system() == "Darwin" else 19


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
    return recvall(sock, msglen)


try:
    with open("client_config.json", "r") as configFile:
        config = json.load(configFile)
except FileNotFoundError:
    print("Warning: client_config.json not found, client will close.")
    sys.exit("No config file. Please create client_config.json.")

client = None
key_map = {}
valid_public_keys = []
valid_private_keys = []
last_activity = None
client_timeout = 180  # 3 minutes
selected_public_key = None

HOST_ADDR = config.get("server", "")
HOST_PORT = config.get("port", 13031)
debug_mode = config.get("debug", False)

if not HOST_ADDR or not HOST_PORT:
    sys.exit("No server IP or PORT in configuration.")

try:
    gpg = gnupg.GPG()
    public_keys = gpg.list_keys()
    private_keys = gpg.list_keys(True)
    if debug_mode:
        print("=== DEBUG: Private keys found ===")
        for key in private_keys:
            print(f"  Key ID: {key['keyid']}, UID: {key.get('uids', [])}")
except Exception as e:
    print(f"Critical Error: GPG not installed or in PATH: {e}")
    sys.exit("Please install GPG on your system (e.g., brew install gnupg)")

GPGuidDestino = config.get("GPGid", "182DA782")


def is_valid_key(key):
    return not key.get("expired", False) and not key.get("revoked", False)


valid_public_keys = sorted(
    [key for key in public_keys if is_valid_key(key)],
    key=lambda k: k.get("uids", [""])[0],
    reverse=True,
)
valid_private_keys = sorted(
    [key for key in private_keys if is_valid_key(key)],
    key=lambda k: k.get("uids", [""])[0],
    reverse=True,
)

window = tk.Tk()
window.title("Cliente v 2.7 (VerySecureChat)")
username = " "

BG_COLOR = "#1a1b26"
FG_COLOR = "#c0caf5"
ACCENT = "#7aa2f7"
BTN_BG = "#3d59a1"
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
    # Pre-select the saved GPGid from config
    saved_gpgid = config.get("GPGid", "")
    if saved_gpgid and saved_gpgid in keyNames:
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
key_map = {}  # tkUserList index -> key dict
tkUserList.insert(0, "<SELECT RECIPIENT>")
for i, key in enumerate(valid_public_keys, start=1):
    val = key["uids"][0] if key.get("uids") else "Unknown ID"
    tkUserList.insert(i, val)
    key_map[i] = key
tkUserList.select_set(0)


def reload_keys():
    global public_keys, private_keys, valid_public_keys, valid_private_keys, key_map
    try:
        public_keys = gpg.list_keys()
        private_keys = gpg.list_keys(True)
        valid_public_keys = sorted(
            [key for key in public_keys if is_valid_key(key)],
            key=lambda k: k.get("uids", [""])[0],
            reverse=True,
        )
        valid_private_keys = sorted(
            [key for key in private_keys if is_valid_key(key)],
            key=lambda k: k.get("uids", [""])[0],
            reverse=True,
        )

        tkUserList.delete(0, tk.END)
        key_map = {}
        tkUserList.insert(0, "<SELECT RECIPIENT>")
        for i, key in enumerate(valid_public_keys, start=1):
            val = key["uids"][0] if key.get("uids") else "Unknown ID"
            tkUserList.insert(i, val)
            key_map[i] = key
        tkUserList.select_set(0)
        if debug_mode:
            print("GPG keys reloaded.")
    except Exception as e:
        messagebox.showerror("ERROR!!!", f"Failed to reload GPG: {e}")


def connect():
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

    # Save the selected GPG private key ID to config
    saved_gpgid = config.get("GPGid", "")
    if username != saved_gpgid:
        config["GPGid"] = username
        with open("client_config.json", "w") as configFile:
            json.dump(config, configFile, indent=2)

    connect_to_server(username)


def connect_to_server(name):
    global client, last_activity
    try:
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

        threading.Thread(
            target=receive_message_from_server, args=(client,), daemon=True
        ).start()
    except Exception as e:
        messagebox.showerror(
            "ERROR!!!", f"Error connecting to server {HOST_ADDR}:{HOST_PORT}.\n{e}"
        )


def handle_disconnection():
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


def start_client_timeout_check():
    window.after(30000, check_client_timeout)


def check_client_timeout():
    global last_activity, client
    if client is not None and last_activity is not None:
        if time.time() - last_activity > client_timeout:
            if debug_mode:
                print("Client timeout: disconnecting due to inactivity")
            handle_disconnection()
        else:
            start_client_timeout_check()


def insert_text_safe(text, tag=None):
    def _insert():
        tkDisplay.config(state="normal")
        if tag:
            tkDisplay.insert(tk.END, text, tag)
        else:
            tkDisplay.insert(tk.END, text)
        tkDisplay.config(state="disabled")
        tkDisplay.see(tk.END)

    window.after(0, _insert)


def receive_message_from_server(sck):
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
            if debug_mode:
                print(f"Message acknowledged by server: {from_server}")
            continue

        last_activity = time.time()

        cuando = datetime.datetime.now()

        if "-----BEGIN PGP" in from_server:
            if debug_mode:
                print(
                    f"--- RECEIVED ENCRYPTED ---\n{from_server[:100]}...\n--- END ---"
                )
            try:
                # Convert string to bytes for GPG
                encrypted_bytes = from_server.encode("utf-8")

                # First try simple decrypt
                decrypted_data = gpg.decrypt(encrypted_bytes)

                if not decrypted_data.ok:
                    # Try with --try-all-secrets as fallback
                    decrypted_data = gpg.decrypt(
                        encrypted_bytes, extra_args=["--try-all-secrets"]
                    )

                print(
                    f"[RECV] decrypt ok={decrypted_data.ok}, status={decrypted_data.status}"
                )

                if decrypted_data.ok:
                    data = decrypted_data.data
                    if isinstance(data, bytes):
                        data = data.decode("utf-8", errors="replace")
                    print(f"[RECV] decrypted: {data}")
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
                if debug_mode:
                    print(f"[DECRYPT] Exception: {e}")
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


def getChatMessage(msg):
    global last_activity
    msg = msg.strip()
    if not msg:
        return
    last_activity = time.time()
    cuando = datetime.datetime.now()

    insert_text_safe(f"OUT-{cuando} - {msg}\n", "tag_your_message")
    send_msg_to_server(msg)

    tkMessage.delete("1.0", tk.END)


def send_msg_to_server(msg):
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

            if debug_mode:
                print(
                    f"[SEND] Encrypting to recipient={recipient}, keyid={recipient_keyid}, fingerprint={recipient_fingerprint}"
                )

            # Use fingerprint if available, otherwise keyid
            encrypt_key = recipient_fingerprint or recipient_keyid
            try:
                # Encrypt using the key directly
                encrypted_data = gpg.encrypt(client_msg, encrypt_key, always_trust=True)
                if not encrypted_data.ok:
                    if debug_mode:
                        print(
                            f"SEND: {cuando}. OK: False (Key for {recipient} unusable)"
                        )
                    continue

                encrypted_string = str(encrypted_data)
                if debug_mode:
                    print(f"SEND: {cuando}. OK: True")
                    print(f"--- SENT ENCRYPTED ---\n{encrypted_string}\n--- END ---")
                send_data(client, encrypted_string.encode("utf-8"))
                time.sleep(0.2)
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
