"""GhostPay dashboard. Run on Windows:  streamlit run app.py
Needs in the same folder: engine.py, audit.py, beneficiaries.csv, deceased.csv"""
import pandas as pd
import streamlit as st
from engine import load_screener
from audit import HashChainLog

st.set_page_config(page_title="GhostPay", page_icon="🛡️", layout="wide")

@st.cache_resource
def get_screener():
    return load_screener()

@st.cache_data
def get_registry():
    return pd.read_csv("beneficiaries.csv", dtype=str)

screener, reg = get_screener(), get_registry()
if "log" not in st.session_state:
    st.session_state.log = HashChainLog()
log = st.session_state.log

def show_result(res):
    msg = f"**{res['decision']}**: {res['reason']}  \nDecision time: {res['latency_ms']:.4f} ms"
    {"PAY": st.success, "HOLD": st.warning, "BLOCK": st.error}[res["decision"]](msg)

st.title("🛡️ GhostPay")
st.caption("Real-time Pay / Hold / Block screening for welfare disbursements. "
           "Synthetic data only. Decision support: held cases go to human verification.")
t1, t2, t3 = st.tabs(["Check one payment", "Run a payment batch", "Audit log"])

# ---------- Tab 1 ----------
with t1:
    mode = st.radio("Mode", ["Pick from registry", "Enter a new payment manually"], horizontal=True)
    if mode == "Pick from registry":
        kind = st.selectbox("Example type", sorted(reg["planted"].unique()),
                            index=sorted(reg["planted"].unique()).index("duplicate")
                            if "duplicate" in set(reg["planted"]) else 0)
        subset = reg[reg["planted"] == kind].head(200)
        rid = st.selectbox("Record", subset["id"].tolist())
        rec = subset[subset["id"] == rid].iloc[0].to_dict()
        c = st.columns(5)
        c[0].write(f"**Name**\n\n{rec['name']}"); c[1].write(f"**DOB**\n\n{rec['dob']}")
        c[2].write(f"**Phone**\n\n{rec['phone']}"); c[3].write(f"**Account**\n\n{rec['account']}")
        c[4].write(f"**Amount**\n\n₹{rec['amount']}")
        payment = rec
    else:
        st.info("Tip: copy a name and DOB from a registry record, change one letter, and use a new account. "
                "GhostPay should block it as a duplicate.")
        a, b = st.columns(2)
        name = a.text_input("Name"); dob = b.text_input("Date of birth (YYYY-MM-DD)")
        phone = a.text_input("Phone", "9000000000"); account = b.text_input("Account", "999999999999")
        amount = st.number_input("Amount (₹)", 100, 100000, 1000)
        payment = {"id": "NEW", "name": name, "dob": dob, "phone": phone,
                   "account": account, "amount": amount}
    if st.button("Screen payment", type="primary"):
        if not payment["name"] or not payment["dob"]:
            st.warning("Enter a name and date of birth.")
        else:
            res = screener.screen(payment)
            show_result(res)
            log.append({"payment": str(payment["id"]), "decision": res["decision"], "reason": res["reason"]})

# ---------- Tab 2 ----------
with t2:
    n = st.slider("Payments in this batch", 500, len(reg), min(5000, len(reg)), step=500)
    if st.button("Run batch", type="primary"):
        sample = reg.sample(n, random_state=7)
        rows = []
        for rec in sample.to_dict("records"):
            r = screener.screen(rec)
            rows.append({"id": rec["id"], "name": rec["name"], "amount": int(rec["amount"]),
                         "decision": r["decision"], "reason": r["reason"],
                         "planted": rec["planted"], "ms": r["latency_ms"]})
            if r["decision"] != "PAY":
                log.append({"payment": rec["id"], "decision": r["decision"], "reason": r["reason"]})
        df = pd.DataFrame(rows)
        st.session_state.batch = df
    if "batch" in st.session_state:
        df = st.session_state.batch
        m = st.columns(4)
        for col, d in zip(m, ["PAY", "HOLD", "BLOCK"]):
            sub = df[df["decision"] == d]
            col.metric(d, f"{len(sub)}", f"₹{sub['amount'].sum():,}", delta_color="off")
        m[3].metric("p99 decision time", f"{df['ms'].quantile(.99):.4f} ms")
        st.subheader("Cases needing action (Hold / Block)")
        st.dataframe(df[df["decision"] != "PAY"][["id", "name", "amount", "decision", "reason"]],
                     use_container_width=True, hide_index=True)
        st.subheader("Result by planted type (ground truth)")
        st.dataframe(pd.crosstab(df["planted"], df["decision"]), use_container_width=True)

# ---------- Tab 3 ----------
with t3:
    st.write(f"Entries in the hash-chained log: **{len(log.entries)}**")
    ok, bad = log.verify()
    (st.success if ok else st.error)("Log intact" if ok else f"TAMPERING DETECTED at entry #{bad}")
    if log.entries:
        k = st.number_input("Entry to tamper with", 0, len(log.entries) - 1, 0)
        c1, c2 = st.columns(2)
        if c1.button("Simulate an insider editing this entry"):
            log.entries[int(k)]["data"]["decision"] = "PAY"
            st.rerun()
        if c2.button("Reset log"):
            st.session_state.log = HashChainLog(); st.rerun()
        st.dataframe(pd.DataFrame([{"#": i, **e["data"], "hash": e["hash"][:12]}
                                   for i, e in enumerate(log.entries[-50:], max(0, len(log.entries) - 50))]),
                     use_container_width=True, hide_index=True)
