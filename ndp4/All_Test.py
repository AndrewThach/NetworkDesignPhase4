import subprocess
import time
import csv
import os
import sys

SERVER_PORT = 12000
WINDOW_SIZE = 5
TIMEOUT = 0.10
INPUT_FILE = "send.bin"
OUTPUT_FILE = "received.bin"

PYTHON_EXE = sys.executable

LOSS_VALUES = [i / 100 for i in range(0, 100, 5)]   # 0.00 to 0.95
OPTIONS = [1, 2, 3, 4, 5]
RUNS_PER_POINT = 1


def delete_file_if_exists(filename):
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except OSError:
            pass


def files_match(file1, file2):
    if not os.path.exists(file1) or not os.path.exists(file2):
        return False

    with open(file1, "rb") as f1, open(file2, "rb") as f2:
        return f1.read() == f2.read()


def run_one_test(option, loss):
    delete_file_if_exists(OUTPUT_FILE)

    server_cmd = [
        PYTHON_EXE,
        "server_gbn_phase4.py",
        str(SERVER_PORT),
        str(option),
        str(loss),
        OUTPUT_FILE
    ]

    client_cmd = [
        PYTHON_EXE,
        "client_gbn_phase4.py",
        "127.0.0.1",
        str(SERVER_PORT),
        str(option),
        str(loss),
        str(WINDOW_SIZE),
        str(TIMEOUT),
        INPUT_FILE
    ]

    server = subprocess.Popen(
        server_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(0.15)

    start_time = time.time()

    client_result = subprocess.run(
        client_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    end_time = time.time()

    if server.poll() is None:
        server.terminate()
        try:
            server.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            server.kill()

    elapsed = end_time - start_time
    success = (client_result.returncode == 0) and files_match(INPUT_FILE, OUTPUT_FILE)

    return elapsed, success


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found")
        return

    results = []

    print("Running Phase 4 tests...")

    for option in OPTIONS:
        print(f"\n===== OPTION {option} =====")

        for loss in LOSS_VALUES:
            times = []
            success_count = 0

            for _ in range(RUNS_PER_POINT):
                elapsed, success = run_one_test(option, loss)
                times.append(elapsed)
                if success:
                    success_count += 1

            avg_time = sum(times) / len(times)

            results.append([
                option,
                loss,
                round(avg_time, 4),
                success_count,
                RUNS_PER_POINT
            ])

            print(f"loss={loss:.2f}  avg={avg_time:.4f}s  success={success_count}/{RUNS_PER_POINT}")

    with open("phase4_results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Option", "Loss", "AverageTime", "SuccessCount", "TotalRuns"])
        writer.writerows(results)

    print("\nResults saved to phase4_results.csv")


if __name__ == "__main__":
    main()