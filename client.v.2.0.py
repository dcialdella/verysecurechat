# Client define server ip / port 13031
# v 2.0 - minor changes
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
    return recvall(sock, msglen)

try:
    with open('client_config.json', "r") as configFile:
        config = json.load(configFile)
except FileNotFoundError:
    print("Warning: No se encontro client_config.json, se cerrara el cliente.")
    sys.exit('No config file. Please create client_config.json.')

client = None
key_map = {}
valid_public_keys = []
valid_private_keys = []

HOST_ADDR = config.get('server', '')
HOST_PORT = config.get('port', 13031)
debug_mode = config.get('debug', False)

if not HOST_ADDR or not HOST_PORT:
    sys.exit('No server IP or PORT en la configuracion.')

try:
    gpg = gnupg.GPG()
    public_keys = gpg.list_keys()
    private_keys = gpg.list_keys(True)
except Exception as e:
    print(f"Error critico: GPG no instalado o en PATH: {e}")
    sys.exit("Por favor instala GPG en tu sistema (ej. brew install gnupg)")

GPGuidDestino = config.get('GPGid', "182DA782")

def is_valid_key(key):
    return not key.get('expired', False) and not key.get('revoked', False)

valid_public_keys = [key for key in public_keys if is_valid_key(key)]
valid_private_keys = [key for key in private_keys if is_valid_key(key)]

window = tk.Tk()
window.title("Cliente v 2.1 (VerySecureChat)")
username = " "

BG_COLOR = "#1a1b26"
FG_COLOR = "#c0caf5"
ACCENT = "#7aa2f7"
BTN_BG = "#3d59a1"
window.configure(bg=BG_COLOR)

style = ttk.Style()
try: 
    style.theme_use('clam')
except Exception: 
    pass
style.configure("TFrame", background=BG_COLOR)
style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=("Helvetica", 12))
style.configure("TButton", background=BTN_BG, foreground="white", font=("Helvetica", 11, "bold"), padding=3)
style.map("TButton", background=[("active", ACCENT)])

topFrame = ttk.Frame(window)
ttk.Label(topFrame, text="GPG U.ID:").pack(side=tk.LEFT, padx=5)
entNameText = tk.StringVar()
entName = ttk.Combobox(topFrame, width=50, textvariable=entNameText)
entName.pack(side=tk.LEFT, padx=5)

keyNames = [key['uids'][0] for key in valid_private_keys] if valid_private_keys else ["<Ninguna Clave Privada GPG>"]
entName['values'] = keyNames
if keyNames: 
    entNameText.set(keyNames[0])

btnConnect = ttk.Button(topFrame, text="Conectar", command=lambda: connect())
btnConnect.pack(side=tk.LEFT, padx=5)
btnDisconnect = ttk.Button(topFrame, text="Desconectar", command=lambda: handle_disconnection())
btnDisconnect.state(["disabled"])
btnDisconnect.pack(side=tk.LEFT, padx=5)
btnReload = ttk.Button(topFrame, text="🔄 Recargar Llaves", command=lambda: reload_keys())
btnReload.pack(side=tk.LEFT, padx=5)
topFrame.pack(side=tk.TOP, pady=15)

displayFrame = ttk.Frame(window)
scrollBar = tk.Scrollbar(displayFrame)
scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
tkDisplay = tk.Text(displayFrame, height=25, width=65, bg="#24283b", fg=FG_COLOR, font=("Helvetica", 12), insertbackground=FG_COLOR, highlightthickness=0, borderwidth=1)
tkDisplay.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0))
tkDisplay.tag_config("tag_your_message",  foreground="#9ece6a")
tkDisplay.tag_config("tag_your_message2", foreground="#7aa2f7")
scrollBar.config(command=tkDisplay.yview)
tkDisplay.config(yscrollcommand=scrollBar.set, state="disabled")
displayFrame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10)

bottomFrame = ttk.Frame(window)
ttk.Label(bottomFrame, text="Mensaje:").pack(side=tk.LEFT, padx=5)
tkMessage = tk.Text(bottomFrame, height=4, width=70, bg="#24283b", fg=FG_COLOR, font=("Helvetica", 12), insertbackground=FG_COLOR, highlightthickness=0, borderwidth=1)
tkMessage.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5), pady=(10, 15))
tkMessage.config(state="disabled")
tkMessage.bind("<Return>", (lambda event: (getChatMessage(tkMessage.get("1.0", tk.END)), "break")))
bottomFrame.pack(side=tk.BOTTOM, fill=tk.X)

tkUserList = tk.Listbox(displayFrame, height=25, width=36, exportselection=False, bg="#24283b", fg=FG_COLOR, selectbackground=ACCENT, selectforeground="#000000", highlightthickness=0, font=("Helvetica", 12))
tkUserList.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
key_map = {}  # tkUserList index -> key dict
tkUserList.insert(0, '<SELECCIONE DESTINO>')
tkUserList.insert(1, '<Todos>')
for i, key in enumerate(valid_public_keys, start=2):
    val = key['uids'][0] if key.get('uids') else 'Unknown ID'
    tkUserList.insert(i, val)
    key_map[i] = key
tkUserList.select_set(0)

def reload_keys():
    global public_keys, private_keys, valid_public_keys, valid_private_keys, key_map
    try:
        public_keys = gpg.list_keys()
        private_keys = gpg.list_keys(True)
        valid_public_keys = [key for key in public_keys if is_valid_key(key)]
        valid_private_keys = [key for key in private_keys if is_valid_key(key)]
        
        tkUserList.delete(0, tk.END)
        key_map = {}
        tkUserList.insert(0, '<SELECCIONE DESTINO>')
        tkUserList.insert(1, '<Todos>')
        for i, key in enumerate(valid_public_keys, start=2):
            val = key['uids'][0] if key.get('uids') else 'Unknown ID'
            tkUserList.insert(i, val)
            key_map[i] = key
        tkUserList.select_set(0)
        if debug_mode: 
            print("Claves PGP recargadas en vivo.")
    except Exception as e:
        messagebox.showerror("ERROR!!!", f"Fallo al recargar GPG: {e}")

def connect():
    global username, client
    if not valid_private_keys:
        messagebox.showerror("ERROR!!!", "No tienes claves privadas GPG validas para usar el chat.")
        return
        
    if len(entName.get()) < 1:
        messagebox.showerror("ERROR!!!", "Debes indicar tu ID de GPG.")
    else:
        username = entName.get()
        connect_to_server(username)

def connect_to_server(name):
    global client
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST_ADDR, HOST_PORT))
        send_data(client, name.encode('utf-8'))

        entName.config(state="disabled")
        btnConnect.state(["disabled"])
        btnDisconnect.state(["!disabled"])
        tkMessage.config(state="normal")
        tkMessage.focus_set()

        threading.Thread(target=receive_message_from_server, args=(client,), daemon=True).start()
    except Exception as e:
        messagebox.showerror("ERROR!!!", f"Error al conectar al servidor {HOST_ADDR}:{HOST_PORT}.\n{e}")

def handle_disconnection():
    global client
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
    insert_text_safe("\n--- DESCONECTADO DEL SERVIDOR ---\n", "tag_your_message")

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
    while True:
        try:
            raw = recv_data(sck)
            if raw is None: 
                break
            from_server = raw.decode('utf-8', errors='replace')
        except Exception:
            break
            
        if from_server == "SYS:PING":
            try: 
                send_data(sck, b"SYS:PONG")
            except Exception:
                pass
            continue

        cuando = datetime.datetime.now()

        if 'PGP MESSAGE' in from_server:
            decrypted_data = gpg.decrypt(from_server)
            if decrypted_data.ok:
                insert_text_safe(f"IN: {cuando} - {decrypted_data.data.decode(errors='replace')}\n", "tag_your_message2")
            else:
                if debug_mode: 
                    print('Error desencriptando.', decrypted_data.status)
        else:
            insert_text_safe(f"IN: {cuando} - {from_server}", "tag_your_message2")

    try:
        sck.close()
    except Exception:
        pass
    window.after(0, handle_disconnection)

def getChatMessage(msg):
    msg = msg.replace('\n', '')
    cuando = datetime.datetime.now()

    insert_text_safe(f"OUT-{cuando} - {msg}\n", "tag_your_message")
    send_msg_to_server(msg)

    tkMessage.delete('1.0', tk.END)

def send_msg_to_server(msg):
    global client
    client_msg = str(msg)

    if client_msg == "fin":
        window.destroy()
        sys.exit(0)

    if len(client_msg) > 0:
        selections = tkUserList.curselection()
        if not selections or selections[0] == 0:
            messagebox.showwarning("Destino Inválido", "Tienes seleccionado <SELECCIONE DESTINO>.\nPor seguridad humana, por favor selecciona a qué contacto o grupo enviarás este mensaje.")
            return
            
        if selections[0] == 1:
            destKeys = valid_public_keys
        else:
            destKeys = [key_map.get(selections[0])]
            if not destKeys[0]:
                messagebox.showerror("ERROR", "Destino inválido.")
                return

        for key in destKeys:
            destino = key['uids'][0] if key.get('uids') else ''
            cuando = datetime.datetime.now()

            try:
                encrypted_data = gpg.encrypt(client_msg, destino, always_trust=True)
                if not encrypted_data.ok:
                    if debug_mode: 
                        print(f"MANDO: {cuando}. OK: False (Clave de {destino} inutilizable)")
                    continue
                
                encrypted_string = str(encrypted_data)
                if debug_mode: 
                    print(f"MANDO: {cuando}. OK: True")
                send_data(client, encrypted_string.encode('utf-8'))
            except Exception as e:
                insert_text_safe(f"Error en envio a {destino}: {e}\n", "tag_your_message2")

window.update_idletasks()
w = window.winfo_width()
h = window.winfo_height()
x = (window.winfo_screenwidth() // 2) - (w // 2)
y = (window.winfo_screenheight() // 2) - (h // 2)
window.geometry(f"+{x}+{y}")
window.minsize(w, h)

window.mainloop()
