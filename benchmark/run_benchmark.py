"""
Benchmark harness - mjeri vrijeme enkripcije/dekripcije za sve algoritme
kroz razlicite velicine podataka. Rezultati idu u thesis poglavlje 3.5.

Pokreni: python benchmark/run_benchmark.py
"""
import os
import sys
import time

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import aes, des, rsa  # noqa: E402  (dodaj ecc, chacha kad budu ukljuceni)

DATA_SIZES = [1_000, 10_000, 100_000, 1_000_000]  # bajtovi
REPEATS = 20


def time_function(func, *args, repeats=REPEATS) -> float:
    """Vraca prosjecno vrijeme izvrsavanja u sekundama."""
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        func(*args)
        times.append(time.perf_counter() - start)
    return sum(times) / len(times)


def run_all():
    results = []
    for size in DATA_SIZES:
        data = os.urandom(size)
        # TODO: dodaj poziv za svaki algoritam kad core/ bude implementiran, npr:
        #
        # keys = aes.generate_keys(128)
        # avg_time = time_function(aes.encrypt, data, keys["key"])
        # results.append({"algoritam": "AES-128", "velicina": size, "vrijeme": avg_time})
        pass

    df = pd.DataFrame(results)
    df.to_csv(os.path.join(os.path.dirname(__file__), "results.csv"), index=False)
    print(df)


if __name__ == "__main__":
    run_all()
