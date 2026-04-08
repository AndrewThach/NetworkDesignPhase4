from socket import *
import sys
import time
import random
from rdt_utils_phase4 import (
    TYPE_ACK,
    FLAG_EOF,
    make_packet,
    parse_packet,
    is_corrupt,
    flip_one_bit,
    chunk_file,
)

"""
Usage:
python client_gbn_phase4.py <server_ip> <port> <option> <probability> <window_size> <timeout_sec> <input_file>

Example:
python client_gbn_phase4.py 127.0.0.1 12000 4 0.20 5 0.25 send.bmp

Options:
1 = no loss / no bit errors
2 = ACK bit error at sender      (client corrupts received ACK before verifying it)
3 = DATA bit error at receiver   (client behaves normally)
4 = ACK loss at sender           (client intentionally drops received ACK)
5 = DATA loss at receiver        (client behaves normally)
"""


def should_inject(probability: float) -> bool:
    return random.random() < probability


def load_data_packets(input_file: str):
    chunks = list(chunk_file(input_file))
    packets = {}

    seq_num = 1
    total = len(chunks)

    if total == 0:
        # Allow empty-file transfer with one EOF packet
        packets[1] = make_packet(0, 1, b"", FLAG_EOF)
        return packets

    i = 0
    while i < total:
        flags = FLAG_EOF if i == total - 1 else 0
        packets[seq_num] = make_packet(0, seq_num, chunks[i], flags)
        seq_num += 1
        i += 1

    return packets


def main():
    if len(sys.argv) != 8:
        print("Usage: python client_gbn_phase4.py <server_ip> <port> <option> <probability> <window_size> <timeout_sec> <input_file>")
        sys.exit(1)

    server_ip = sys.argv[1]
    port = int(sys.argv[2])
    option = int(sys.argv[3])
    probability = float(sys.argv[4])
    window_size = int(sys.argv[5])
    timeout_interval = float(sys.argv[6])
    input_file = sys.argv[7]

    if option not in (1, 2, 3, 4, 5):
        print("Option must be 1, 2, 3, 4, or 5")
        sys.exit(1)

    packets = load_data_packets(input_file)
    total_packets = len(packets)

    client_socket = socket(AF_INET, SOCK_DGRAM)
    client_socket.settimeout(0.02)

    server_addr = (server_ip, port)

    base = 1
    next_seq_num = 1
    timer_start = None

    print(f"Client sending {total_packets} packets")
    print(f"Option={option}, probability={probability}, window={window_size}, timeout={timeout_interval}s")

    start_time = time.time()

    while base <= total_packets:
        # Send packets while window has space
        while next_seq_num < base + window_size and next_seq_num <= total_packets:
            client_socket.sendto(packets[next_seq_num], server_addr)
            print(f"Sent packet {next_seq_num}")

            if base == next_seq_num:
                timer_start = time.time()

            next_seq_num += 1

        # Try receiving ACKs
        try:
            ack_packet, _ = client_socket.recvfrom(2048)

            # Option 4: intentional ACK loss at sender
            if option == 4 and should_inject(probability):
                print("Injected ACK loss at sender")
                raise timeout("Intentional ACK drop")

            # Option 2: intentional ACK bit error at sender
            if option == 2 and should_inject(probability):
                ack_packet = flip_one_bit(ack_packet)
                print("Injected ACK bit error at sender")

            if is_corrupt(ack_packet):
                print("Corrupted ACK ignored")
            else:
                packet_type, ack_num, payload_len, checksum, flags, payload = parse_packet(ack_packet)

                if packet_type == TYPE_ACK:
                    print(f"Received ACK {ack_num}")
                    if ack_num >= base:
                        base = ack_num + 1
                        if base == next_seq_num:
                            timer_start = None
                        else:
                            timer_start = time.time()

        except timeout:
            pass

        # Check timer for oldest unacked packet
        if timer_start is not None and (time.time() - timer_start) >= timeout_interval:
            print(f"Timeout at base={base}. Retransmitting window...")
            seq = base
            while seq < next_seq_num:
                client_socket.sendto(packets[seq], server_addr)
                print(f"Resent packet {seq}")
                seq += 1
            timer_start = time.time()

    end_time = time.time()
    client_socket.close()

    print(f"Transfer complete in {end_time - start_time:.4f} seconds")


if __name__ == "__main__":
    main()
