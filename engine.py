"""GhostPay core engine: screen_payment(payment) -> PAY / HOLD / BLOCK + reason."""
import csv, os, re, time
from collections import defaultdict
from difflib import SequenceMatcher

NAME_SIM_BLOCK = 0.90   # name similarity (same DOB) -> BLOCK as duplicate
ACCOUNT_LIMIT = 3       # other beneficiaries on the same account -> HOLD
PHONE_LIMIT = 3         # other beneficiaries on the same phone   -> HOLD


def norm_name(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", "", str(s).lower())).strip()

def norm_digits(s):
    return re.sub(r"\D", "", str(s))[-12:]

def norm_dob(s):
    return str(s).strip()[:10]


class Screener:
    def __init__(self):
        self.by_dob = defaultdict(list)      # dob -> [(seq, id, normname)]
        self.by_account = defaultdict(set)   # account -> {ids}
        self.by_phone = defaultdict(set)     # phone -> {ids}
        self.deceased = set()                # "normname|dob"
        self.seq = {}                        # id -> enrolment order

    def add_registry(self, rec):
        i, n = rec["id"], norm_name(rec["name"])
        self.seq[i] = int(rec.get("seq", len(self.seq)))
        self.by_dob[norm_dob(rec["dob"])].append((self.seq[i], i, n))
        self.by_account[norm_digits(rec["account"])].add(i)
        self.by_phone[norm_digits(rec["phone"])].add(i)

    def add_deceased(self, name, dob):
        self.deceased.add(f"{norm_name(name)}|{norm_dob(dob)}")

    def screen(self, p):
        t0 = time.perf_counter()
        decision, reason = self._decide(p)
        ms = (time.perf_counter() - t0) * 1000
        return {"decision": decision, "reason": reason, "latency_ms": ms}

    def _decide(self, p):
        pid = p.get("id")
        name, dob = norm_name(p["name"]), norm_dob(p["dob"])
        # 1. deceased list -> BLOCK
        if f"{name}|{dob}" in self.deceased:
            return "BLOCK", "Beneficiary is on the deceased-persons list"
        # 2. duplicate: same DOB + similar name, enrolled EARLIER -> BLOCK
        my_seq = self.seq.get(pid, 10**12)
        for seq, oid, oname in self.by_dob.get(dob, ()):
            if oid == pid or seq >= my_seq:
                continue
            m = SequenceMatcher(None, name, oname)
            if m.real_quick_ratio() >= NAME_SIM_BLOCK and m.quick_ratio() >= NAME_SIM_BLOCK:
                r = m.ratio()
                if r >= NAME_SIM_BLOCK:
                    return "BLOCK", f"Duplicate of {oid}: same DOB, name {r:.0%} similar"
        # 3. shared account / phone -> HOLD
        acc = self.by_account.get(norm_digits(p["account"]), set()) - {pid}
        if len(acc) >= ACCOUNT_LIMIT:
            return "HOLD", f"Same account linked to {len(acc)+1} beneficiaries"
        ph = self.by_phone.get(norm_digits(p["phone"]), set()) - {pid}
        if len(ph) >= PHONE_LIMIT:
            return "HOLD", f"Same phone linked to {len(ph)+1} beneficiaries"
        return "PAY", "No risk signals found"


def load_screener(reg_csv="beneficiaries.csv", dec_csv="deceased.csv"):
    s = Screener()
    if os.path.exists(reg_csv):
        with open(reg_csv, newline="") as f:
            for r in csv.DictReader(f):
                s.add_registry(r)
    if os.path.exists(dec_csv):
        with open(dec_csv, newline="") as f:
            for r in csv.DictReader(f):
                s.add_deceased(r["name"], r["dob"])
    return s


_default = None
def screen_payment(payment: dict) -> dict:
    """Interface contract for the whole team."""
    global _default
    if _default is None:
        _default = load_screener()
    return _default.screen(payment)
