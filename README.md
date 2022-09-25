# VerySecureChat
Very Secure Chat using GPG as encription system
v0.0.1 - GPL v2.0
Linux Only (NOW)

Server runs on port 13031 - hostname defined in SERVER Python code
Clients runs and connect to SERVER name, port 13031.

Clientes connect to server, and send PGP message to server, server deliver it to all clientes.

Every client will encript message before send it. Encrypt END-END

Every client will try to de-crypt message, if the message is not PGP, will be show as it.

You need GPG instgalled and Pub/Priv key (you) and PUB keys for others.
You have PRIV/PUB key for your GPG U ID and the Pub KEY for GENERAL UID

Tested in xUbuntu.

For WINDOWS
https://gpg4win.org/download.html

For OSX
https://gpgtools.org/

Must create GPG pub/priv key
gpg --full-generate-key

gpg –list-secret-keys
gpg –list-public-keys
