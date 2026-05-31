import struct
import logging
from socket import socket as Socket

logger = logging.getLogger(__name__)

MAX_MSG_SIZE: int = 5 * 1024 * 1024


def send_data(sock: Socket, data: bytes) -> None:
    sock.sendall(struct.pack("!I", len(data)))
    sock.sendall(data)


def recvall(sock: Socket, n: int) -> bytes | None:
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)


def recv_data(sock: Socket) -> bytes | None:
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack("!I", raw_msglen)[0]
    if msglen > MAX_MSG_SIZE:
        logger.warning("Payload size limit exceeded: %d bytes", msglen)
        raise ValueError("Payload size limit exceeded")
    return recvall(sock, msglen)
