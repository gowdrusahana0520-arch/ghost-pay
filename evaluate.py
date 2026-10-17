"""Detection rate and false-hold rate against planted ground truth."""
import csv
from collections import Counter
from engine import load_screener

s = load_screener()
tot, flagged, exact = Counter(), Counter(), Counter()
with open("beneficiaries.csv", newline="") as f:
    for r in csv.DictReader(f):
        d = s.screen(r)["decision"]
        k = r["planted"]; tot[k] += 1
        flagged[k] += d != "PAY"
        exact[k] += d == r["label"]

print(f"{'type':16}{'count':>7}{'flagged':>9}{'exact':>8}")
for k in tot:
    print(f"{k:16}{tot[k]:>7}{flagged[k]/tot[k]:>9.1%}{exact[k]/tot[k]:>8.1%}")
ok = tot["genuine"] + tot["genuine_pair"]
fh = flagged["genuine"] + flagged["genuine_pair"]
bad = sum(tot[k] for k in tot if k not in ("genuine", "genuine_pair"))
caught = sum(flagged[k] for k in tot if k not in ("genuine", "genuine_pair"))
print(f"\nDetection rate (planted errors flagged): {caught/bad:.1%}")
print(f"False-hold rate (genuine wrongly flagged): {fh/ok:.2%}")
