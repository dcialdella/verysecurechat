# Client define server ip / port 13031
# v 1.50 - minor changes
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
        if not packet: return None
        data.extend(packet)
    return bytes(data)

def recv_data(sock):
    raw_msglen = recvall(sock, 4)
    if not raw_msglen: return None
    msglen = struct.unpack('!I', raw_msglen)[0]
    return recvall(sock, msglen)

try:
    with open('client_config.json', "r") as configFile:
        config = json.load(configFile)
except FileNotFoundError:
    print("Warning: No se encontro client_config.json, se cerrara el cliente.")
    sys.exit('No config file. Please create client_config.json.')

client = None
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
if not GPGuidDestino:
    GPGuidDestino = "182DA782"

emisorpgp = GPGuidDestino

window = tk.Tk()
window.title("Cliente v 1.50 Refactored")
username = " "

topFrame = tk.Frame(window)
tk.Label(topFrame, text="GPG U.ID:").pack(side=tk.LEFT)
entNameText = tk.StringVar()

entName = ttk.Combobox(topFrame, width=70, textvariable=entNameText)
entName.pack(side=tk.LEFT)

# Validacion rapida para que no crashee sin llaves
keyNames = [key['uids'][0] for key in private_keys] if private_keys else ["<Ninguna Clave Privada GPG>"]

entName['values'] = keyNames
if keyNames:
    entNameText.set(keyNames[0])

btnConnect = tk.Button(topFrame, text="Conectar", command=lambda: connect())
btnConnect.pack(side=tk.LEFT)
topFrame.pack(side=tk.TOP)

displayFrame = tk.Frame(window)
tk.Label(displayFrame, text="*"*69).pack()
scrollBar = tk.Scrollbar(displayFrame)
scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
tkDisplay = tk.Text(displayFrame, height=30, width=70, fg="black")
tkDisplay.pack(side=tk.LEFT, fill=tk.Y, padx=(25, 0))
tkDisplay.tag_config("tag_your_message",  foreground="green")
tkDisplay.tag_config("tag_your_message2", foreground="blue")
scrollBar.config(command=tkDisplay.yview)
tkDisplay.config(yscrollcommand=scrollBar.set, background="#F4F6F7", highlightbackground="grey", state="disabled")
displayFrame.pack(side=tk.TOP)

bottomFrame = tk.Frame(window)
tk.Label(bottomFrame, text="Mensaje:").pack(side=tk.LEFT)
tkMessage = tk.Text(bottomFrame, height=1, width=100)
tkMessage.pack(side=tk.LEFT, padx=(5, 13), pady=(5, 10))
tkMessage.config(highlightbackground="grey", state="disabled")
tkMessage.bind("<Return>", (lambda event: getChatMessage(tkMessage.get("1.0", tk.END))))
bottomFrame.pack(side=tk.BOTTOM)

tkUserList = tk.Listbox(displayFrame, height=30, width=60)
tkUserList.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
tkUserList.insert(0, '<Todos>')
for i, key in enumerate(public_keys, start=1):
    val = key['uids'][0] if key.get('uids') else 'Unknown ID'
    tkUserList.insert(i, val)
tkUserList.select_set(0)

def connect():
    global username, client
    if not private_keys:
        messagebox.showerror("ERROR!!!", "No tienes claves privadas GPG para usar el chat.")
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
        btnConnect.config(state="disabled")
        tkMessage.config(state="normal")
        tkMessage.focus_set()

        threading.Thread(target=receive_message_from_server, args=(client,), daemon=True).start()
    except Exception as e:
        messagebox.showerror("ERROR!!!", f"Error al conectar al servidor {HOST_ADDR}:{HOST_PORT}.\n{e}")

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
            if not raw: break
            from_server = raw.decode('utf-8', errors='replace')
        except:
            break

        cuando = datetime.datetime.now()

        # Check if tkDisplay logic is empty is not safe from threads directly, we skip this tiny detail and dump normally
        if 'PGP MESSAGE' in from_server:
            decrypted_data = gpg.decrypt(from_server)
            if decrypted_data.ok:
                insert_text_safe(f"IN: {cuando} - {decrypted_data.data.decode(errors='replace')}\n", "tag_your_message2")
            else:
                if debug_mode: print('Error desencriptando.', decrypted_data.status)
        else:
            insert_text_safe(f"IN: {cuando} - {from_server}", "tag_your_message2")

    try:
        sck.close()
    except: pass
    window.after(0, window.destroy)

def getChatMessage(msg):
    msg = msg.replace('\n', '')
    cuando = datetime.datetime.now()

    insert_text_safe(f"OUT-{cuando} - {msg}\n", "tag_your_message")
    send_msg_to_server(msg)

    tkMessage.delete('1.0', tk.END)

def send_msg_to_server(msg):
    client_msg = str(msg)

    if client_msg == "fin":
        window.destroy()
        sys.exit(0)

    if len(client_msg) > 0:
        selections = tkUserList.curselection()
        destIdx = selections[0] - 1 if selections else -1
        destKeys = public_keys
        if destIdx >= 0:
            destKeys = [public_keys[destIdx]]

        for key in destKeys:
            destino = key['uids'][0] if key.get('uids') else ''
            cuando = datetime.datetime.now()

            try:
                encrypted_data = gpg.encrypt(client_msg, destino, always_trust=True)
                encrypted_string = str(encrypted_data)

                if debug_mode: print(f"MANDO: {cuando}. OK: {encrypted_data.ok}")
                send_data(client, encrypted_string.encode('utf-8'))
            except Exception as e:
                insert_text_safe(f"Error en envio a {destino}: {e}\n", "tag_your_message2")

window.mainloop()
