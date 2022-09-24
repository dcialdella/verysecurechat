# Client define server ip / port 13031
# v 1.2

import tkinter as tk
from tkinter import messagebox
import socket
import threading
import subprocess
import os

window = tk.Tk()
window.title("Cliente v 1.xxx")
username = " "


# Quien Envia los mensajes
# Tomara el Nombre que definamos al arrancar
userid    = "182DA782"   # ---------------------------------------------

# Para quien seran los mensajes
destinoid = "182DA782"   # ---------------------------------------------


# network client
client = None
HOST_ADDR = "cadorcha.no-ip.com"
HOST_PORT = 13031


topFrame = tk.Frame(window)
lblName = tk.Label(topFrame, text = "Nombre:").pack(side=tk.LEFT)
entName = tk.Entry(topFrame)
entName.pack(side=tk.LEFT)
btnConnect = tk.Button(topFrame, text="Conectar", command=lambda : connect())
btnConnect.pack(side=tk.LEFT)
#btnConnect.bind('<Button-1>', connect)
topFrame.pack(side=tk.TOP)

displayFrame = tk.Frame(window)
lblLine = tk.Label(displayFrame, text="*********************************************************************").pack()
scrollBar = tk.Scrollbar(displayFrame)
scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
tkDisplay = tk.Text(displayFrame, height=30, width=70)
tkDisplay.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
tkDisplay.tag_config("tag_your_message", foreground="blue")
scrollBar.config(command=tkDisplay.yview)
tkDisplay.config(yscrollcommand=scrollBar.set, background="#F4F6F7", highlightbackground="grey", state="disabled")
displayFrame.pack(side=tk.TOP)


bottomFrame = tk.Frame(window)
tkMessage = tk.Text(bottomFrame, height=2, width=55)
tkMessage.pack(side=tk.LEFT, padx=(5, 13), pady=(5, 10))
tkMessage.config(highlightbackground="grey", state="disabled")
tkMessage.bind("<Return>", (lambda event: getChatMessage(tkMessage.get("1.0", tk.END))))
bottomFrame.pack(side=tk.BOTTOM)


def connect():
    global username, client

    if len(entName.get()) < 1:
        tk.messagebox.showerror(title="ERROR!!!", message="Debes indicar tu ID de GPG <ej. 182D2121>")
    else:
        username = entName.get()
        connect_to_server(username)
        userid = username
# GPG ID usado para descriptar


def connect_to_server(name):
    global client, HOST_PORT, HOST_ADDR
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST_ADDR, HOST_PORT))
        client.send(name.encode()) # Send name to server after connecting

        entName.config(state=tk.DISABLED)
        btnConnect.config(state=tk.DISABLED)
        tkMessage.config(state=tk.NORMAL)

        # start a thread to keep receiving message from server
        # do not block the main thread :)
        threading._start_new_thread(receive_message_from_server, (client, "m"))
    except Exception as e:
        tk.messagebox.showerror(title="ERROR!!!", message="No hay conexiones al server: " + HOST_ADDR + " en puerto: " + str(HOST_PORT) + " el Servidor puede estar apagado.")


def receive_message_from_server(sck, m):
    while True:
        from_server = sck.recv(4096).decode()

        if not from_server: break

        # display message from server on the chat window

        # enable the display area and insert the text and then disable.
        # why? Apparently, tkinter does not allow us insert into a disabled Text widget :(
        texts = tkDisplay.get("1.0", tk.END).strip()
        tkDisplay.config(state=tk.NORMAL)

        if len(texts) < 1:
            tkDisplay.insert(tk.END, from_server)
        else:
# si es un mensaje PGP trata de desencriptar
            if 'PGP MESSAGE' in from_server:
                comando='echo "' + from_server + '" | gpg -d -u ' + userid + ' 2> /dev/null '
                salida = subprocess.run(comando, shell=True, timeout=4, check=True, text=True, capture_output=True )
# capturar error de DECOD
#                error  = subprocess.error
#                print( 'LINE  D: ' + str(comando) )
#                print( 'CODED D: ' + str(salida.stdout) )

                tkDisplay.insert(tk.END, "\nIN: " + salida.stdout )
            else:
# Si no es un mensaje PGP lo presenta como esta
                tkDisplay.insert(tk.END, "\nIN: " + from_server )


        tkDisplay.config(state=tk.DISABLED)
        tkDisplay.see(tk.END)

    sck.close()
    window.destroy()


def getChatMessage(msg):
    msg = msg.replace('\n', '')
    texts = tkDisplay.get("1.0", tk.END).strip()

    # enable the display area and insert the text and then disable.
    # why? Apparently, tkinter does not allow use insert into a disabled Text widget :(
    tkDisplay.config(state=tk.NORMAL)

    if len(texts) < 1:
        tkDisplay.insert(tk.END, "\nENTER: " + msg, "tag_your_message") # no line
    else:
        tkDisplay.insert(tk.END, "\nOUT: " + msg, "tag_your_message")
        # aca invoco al S.O.

        send_msg_to_server( msg )

    tkDisplay.config(state=tk.DISABLED)

    tkDisplay.see(tk.END)
    tkMessage.delete('1.0', tk.END)


def send_msg_to_server(msg):
    client_msg = str(msg)

    if client_msg == "fin":
        client.close()
        window.destroy()

    if len(client_msg) >0:
# Des-comentar para ver mensaje en claro
#        print( 'Msg: ' + str(msg) )
#        client.send(client_msg.encode())

# Armo codigo, Encripto e IMPRIMO en PANTALLA 
        comando='echo "' + client_msg + '" | gpg -u ' + destinoid + ' -e -a --no-comment --no-verbose -r ' + destinoid + ' 2> /dev/null '
        salida = subprocess.run(comando, shell=True, timeout=4, check=True, text=True, capture_output=True )

        # validar RETURNCODE, por errores
#        print( 'LINE : ' + str(comando) )
        print( 'MANDO: ' + str(salida.stdout) )
        client.send( salida.stdout.encode() )

window.mainloop()
 
#
# EOF
#
