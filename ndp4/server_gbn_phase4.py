from socket import *
import sys
import random
from rdt_utils_phase4 import (
    TYPE_DATA,
    TYPE_ACK,
    FLAG_EOF,
    make_packet,
    parse_packet,
    is_corrupt,
    flip_one_bit,
)

"""
Usage:
python server_gbn_phase4.py <port> <option> <probability> <output_file>

Example:
python server_gbn_phase4.py 12000 5 0.20 received.bin

Options:
1 = no loss / no bit errors
2 = ACK bit error at sender            (server behaves normally)
3 = DATA bit error at receiver         (server flips DATA before checksum check)
4 = ACK loss at sender                 (server behaves normally)
5 = DATA loss at receiver              (server drops DATA before processing)
"""


def should_inject(probability: float) -> bool:
    return random.random() < probability


def main():
    if len(sys.argv) != 5:
        print("Usage: python server_gbn_phase4.py <port> <option> <probability> <output_file>")
        sys.exit(1)

    port = int(sys.argv[1])
    option = int(sys.argv[2])
    probability = float(sys.argv[3])
    output_file = sys.argv[4]

    if option not in (1, 2, 3, 4, 5):
        print("Option must be 1, 2, 3, 4, or 5")
        sys.exit(1)

    server_socket = socket(AF_INET, SOCK_DGRAM)
    server_socket.bind(("", port))

    expected_seq_num = 1
    last_acked = 0
    eof_received = False

    print(f"Server listening on port {port}")
    print(f"Option={option}, probability={probability}, output={output_file}")

    out_f = open(output_file, "wb")

    try:
        while True:
            packet, client_addr = server_socket.recvfrom(2048)

            # Option 5: intentional DATA packet loss at receiver
            if option == 5 and should_inject(probability):
                print("Injected DATA loss at receiver")
                continue

            # Option 3: intentional DATA packet bit error at receiver
            if option == 3 and should_inject(probability):
                packet = flip_one_bit(packet)
                print("Injected DATA bit error at receiver")

            if is_corrupt(packet):
                ack_packet = make_packet(TYPE_ACK, last_acked)
                server_socket.sendto(ack_packet, client_addr)
                continue

            packet_type, seq_num, payload_len, checksum, flags, payload = parse_packet(packet)

            if packet_type != TYPE_DATA:
                ack_packet = make_packet(TYPE_ACK, last_acked)
                server_socket.sendto(ack_packet, client_addr)
                continue

            if seq_num == expected_seq_num:
                out_f.write(payload)
                last_acked = expected_seq_num
                expected_seq_num += 1

                ack_packet = make_packet(TYPE_ACK, last_acked)
                server_socket.sendto(ack_packet, client_addr)

                if flags & FLAG_EOF:
                    eof_received = True
            else:
                ack_packet = make_packet(TYPE_ACK, last_acked)
                server_socket.sendto(ack_packet, client_addr)

            if eof_received:
                print("EOF delivered in order. Server done.")
                break
    finally:
        out_f.close()
        server_socket.close()


if __name__ == "__main__":
    main()
