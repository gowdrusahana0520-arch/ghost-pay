"""Synthetic beneficiary data with planted errors (ground truth in 'planted')."""
import csv, random, sys
from faker import Faker

N = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
random.seed(42)
fake = Faker("en_IN"); Faker.seed(42)
rows, acc_counter = [], [100000000000]

def new_account():
    acc_counter[0] += random.randint(1, 9)
    return str(acc_counter[0])

def new_phone():
    return str(random.randint(6, 9)) + "".join(random.choices("0123456789", k=9))

def add(name, dob, phone, account, planted, expected):
    rows.append({"id": f"B{len(rows)+1:07d}", "seq": len(rows) + 1, "name": name,
                 "dob": dob, "phone": phone, "account": account,
                 "scheme": random.choice(["Pension", "Scholarship", "Subsidy"]),
                 "amount": random.choice([500, 1000, 1500, 3000, 5000]),
                 "planted": planted, "label": expected})

def person():
    return fake.name(), fake.date_of_birth(minimum_age=18, maximum_age=90).isoformat()

# 1. genuine beneficiaries
for _ in range(N):
    n, d = person(); add(n, d, new_phone(), new_account(), "genuine", "PAY")

# 2. deceased: some genuine people are on the deceased list
deceased = random.sample(rows[:N], max(1, N // 100))
for r in deceased:
    r["planted"], r["label"] = "deceased", "BLOCK"

# 3. duplicates: same person re-enrolled later with a spelling error -> BLOCK
originals = [r for r in rows[:N] if r["planted"] == "genuine" and len(r["name"]) >= 10]
for r in random.sample(originals, max(1, N // 50)):
    n = r["name"]; k = random.randrange(1, len(n) - 1)
    typo = n[:k] + n[k + 1:] if random.random() < 0.5 else n[:k] + random.choice("aeiou") + n[k + 1:]
    add(typo, r["dob"], new_phone(), new_account(), "duplicate", "BLOCK")

# 4. shared bank accounts: 5-8 different people, one account -> HOLD
for _ in range(max(1, N // 500)):
    acc = new_account()
    for _ in range(random.randint(5, 8)):
        n, d = person(); add(n, d, new_phone(), acc, "shared_account", "HOLD")

# 5. shared phone numbers: 4-6 people, one phone -> HOLD
for _ in range(max(1, N // 1000)):
    ph = new_phone()
    for _ in range(random.randint(4, 6)):
        n, d = person(); add(n, d, ph, new_account(), "shared_phone", "HOLD")

# 6. innocent look-alikes: spouses sharing one account -> must stay PAY
for _ in range(max(1, N // 200)):
    acc = new_account()
    for _ in range(2):
        n, d = person(); add(n, d, new_phone(), acc, "genuine_pair", "PAY")

with open("beneficiaries.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with open("deceased.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["name", "dob"])
    for r in deceased: w.writerow([r["name"], r["dob"]])
print(f"Wrote {len(rows)} records, {len(deceased)} deceased")
