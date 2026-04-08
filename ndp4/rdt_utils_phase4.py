import struct
from typing import Tuple

TYPE_DATA = 0
TYPE_ACK = 1

FLAG_EOF = 0x01

HEADER_FORMAT = "!BIHHB"  # type(1), seq_num(4), payload_len(2), checksum(2), flags(1)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 10 bytes
MAX_PACKET_SIZE = 1024
MAX_PAYLOAD_SIZE = MAX_PACKET_SIZE - HEADER_SIZE  # 1014 bytes


def compute_checksum(data: bytes) -> int:
    """
    16-bit one's complement checksum.
    """
    if len(data) % 2 == 1:
        data += b"\x00"

    total = 0
    i = 0
    while i < len(data):
        word = (data[i] << 8) + data[i + 1]
        total += word
        total = (total & 0xFFFF) + (total >> 16)
        i += 2

    return (~total) & 0xFFFF


def make_packet(packet_type: int, seq_num: int, payload: bytes = b"", flags: int = 0) -> bytes:
    payload_len = len(payload)
    header_wo_checksum = struct.pack(HEADER_FORMAT, packet_type, seq_num, payload_len, 0, flags)
    checksum = compute_checksum(header_wo_checksum + payload)
    header = struct.pack(HEADER_FORMAT, packet_type, seq_num, payload_len, checksum, flags)
    return header + payload


def parse_packet(packet: bytes) -> Tuple[int, int, int, int, int, bytes]:
    if len(packet) < HEADER_SIZE:
        raise ValueError("Packet too short")

    packet_type, seq_num, payload_len, checksum, flags = struct.unpack(
        HEADER_FORMAT, packet[:HEADER_SIZE]
    )

    payload = packet[HEADER_SIZE:HEADER_SIZE + payload_len]
    if len(payload) != payload_len:
        raise ValueError("Malformed packet payload length")

    return packet_type, seq_num, payload_len, checksum, flags, payload


def is_corrupt(packet: bytes) -> bool:
    if len(packet) < HEADER_SIZE:
        return True

    try:
        packet_type, seq_num, payload_len, checksum, flags = struct.unpack(
            HEADER_FORMAT, packet[:HEADER_SIZE]
        )
        payload = packet[HEADER_SIZE:HEADER_SIZE + payload_len]
        if len(payload) != payload_len:
            return True

        header_wo_checksum = struct.pack(HEADER_FORMAT, packet_type, seq_num, payload_len, 0, flags)
        calculated = compute_checksum(header_wo_checksum + payload)
        return calculated != checksum
    except Exception:
        return True


def flip_one_bit(packet: bytes) -> bytes:
    """
    Intentionally corrupt the packet by flipping one bit in the first byte
    when possible.
    """
    if not packet:
        return packet

    data = bytearray(packet)
    data[0] ^= 0x01
    return bytes(data)


def chunk_file(file_path: str):
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(MAX_PAYLOAD_SIZE)
            if not chunk:
                break
            yield chunk
