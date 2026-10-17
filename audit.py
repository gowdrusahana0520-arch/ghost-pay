"""Hash-chained audit log + tamper demo."""
import hashlib, json

class HashChainLog:
    def __init__(self): self.entries = []
    def append(self, data: dict):
        prev = self.entries[-1]["hash"] if self.entries else "0" * 64
        body = json.dumps(data, sort_keys=True)
        h = hashlib.sha256((prev + body).encode()).hexdigest()
        self.entries.append({"data": data, "prev": prev, "hash": h})
    def verify(self):
        """Returns (True, None) or (False, index_of_first_bad_entry)."""
        prev = "0" * 64
        for i, e in enumerate(self.entries):
            body = json.dumps(e["data"], sort_keys=True)
            if e["prev"] != prev or hashlib.sha256((prev + body).encode()).hexdigest() != e["hash"]:
                return False, i
            prev = e["hash"]
        return True, None
    def save(self, path="audit_log.jsonl"):
        with open(path, "w") as f:
            for e in self.entries: f.write(json.dumps(e) + "\n")

if __name__ == "__main__":
    log = HashChainLog()
    for i, d in enumerate(["PAY", "BLOCK", "HOLD", "PAY", "BLOCK"]):
        log.append({"payment": f"B{i:03d}", "decision": d})
    print("Before tampering:", log.verify())
    log.entries[2]["data"]["decision"] = "PAY"          # insider edits one record
    ok, bad = log.verify()
    print(f"After tampering: intact={ok}, first bad entry index={bad}")
