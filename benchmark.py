"""Latency benchmark. Run on LinuxONE and report these numbers."""
import csv, platform, random, statistics, time
from engine import load_screener

s = load_screener()
with open("beneficiaries.csv", newline="") as f:
    recs = list(csv.DictReader(f))
random.seed(1)
sample = [random.choice(recs) for _ in range(min(20000, max(len(recs), 5000)))]
for r in sample[:200]: s.screen(r)            # warm-up

lat = []
t0 = time.perf_counter()
for r in sample:
    a = time.perf_counter(); s.screen(r); lat.append((time.perf_counter() - a) * 1000)
total = time.perf_counter() - t0
lat.sort(); q = lambda p: lat[min(len(lat) - 1, int(len(lat) * p))]
print(f"Platform: {platform.machine()} | Python {platform.python_version()}")
print(f"Registry: {len(recs)} records | Decisions timed: {len(lat)}")
print(f"avg {statistics.mean(lat):.4f} ms | p50 {q(.5):.4f} | p95 {q(.95):.4f} | p99 {q(.99):.4f} | max {lat[-1]:.4f}")
print(f"Throughput: {len(lat)/total:,.0f} decisions/sec")
print("Under 100 ms budget:", "YES" if q(.99) < 100 else "NO")
