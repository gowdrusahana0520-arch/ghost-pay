   # HackMates_IBM Z Datathon 2026 Project: GhostPay
   # GhostPay: Real-Time Screening of Welfare Payments

GhostPay checks each welfare payment (pension, scholarship, subsidy) before the money leaves the account and returns **PAY, HOLD or BLOCK** with a plain-language reason. Built for IBM Z Datathon 2026, track *Wildcard: Beyond the Obvious*.

> **Decision support, not a verdict.** HOLD and BLOCK send a case to human verification. All data is synthetic.

## The problem
Welfare schemes lose money to duplicate beneficiaries (same person, spelling variations), payments to deceased persons, and many "different" beneficiaries sharing one bank account or phone. These are usually found by audits weeks later.

## How it works
1. **Normalize** name, date of birth, phone and account.
2. **Deceased list** match: BLOCK.
3. **Duplicate check:** same date of birth and name similarity of at least 90% (`difflib`) with an earlier enrolment: BLOCK.
4. **Shared account or phone:** 3 or more other beneficiaries on the same account or phone: HOLD.
5. Otherwise: PAY.
6. Every decision is written to a **hash-chained audit log**, so later edits are detectable.

Lookups use dictionary indexes (date-of-birth buckets, account, phone), so each decision does not scan the full registry.

## Results (synthetic data, 10,477 records, run on LinuxONE s390x)
**Detection (planted errors as ground truth)**

| Type | Count | Flagged |
|---|---|---|
| Deceased | 100 | 100% |
| Duplicate | 200 | 100% |
| Shared account | 129 | 100% |
| Shared phone | 48 | 100% |
| Genuine | 9,900 | 0.0% wrongly flagged |
| Genuine pairs (spouses sharing an account) | 100 | 0.0% wrongly flagged |

Detection rate 100%, false-hold rate 0.00%. These are results on data planted with the same patterns the rules look for. They show the engine works as designed, not that it would catch all real-world fraud.

**Latency of the screening decision** (Ubuntu 24.04 on IBM Z, s390x, Python 3.12.3, 10,477 decisions)

| avg | p50 | p95 | p99 | max | throughput |
|---|---|---|---|---|---|
| 0.0053 ms | 0.0041 ms | 0.0111 ms | 0.0220 ms | 0.0701 ms | about 182,876 decisions/sec |

This times the decision function with data already in memory. End-to-end latency in a deployed system (network, database, API) would be higher.

## Run it
```
python3 generate_data.py 10000   # synthetic data (needs: pip install faker)
python3 evaluate.py              # detection and false-hold rates
python3 benchmark.py             # latency percentiles
python3 audit.py                 # tamper-detection demo
streamlit run app.py             # dashboard (pip install streamlit pandas)
```
Engine, data generation, evaluation, benchmark and audit run on **LinuxONE Community Cloud (s390x)**. The Streamlit dashboard was run on a Windows laptop, because `pyarrow` did not install on s390x.

## Files
`engine.py` screening logic | `generate_data.py` synthetic data | `evaluate.py` | `benchmark.py` | `audit.py` hash-chained log | `app.py` dashboard | `results_*.txt` raw outputs

## Limitations
- Rule-based with fuzzy matching, not a trained ML model.
- Duplicates are caught only when the date of birth matches; swapped name order and date typos are not handled.
- Synthetic data only. Real deployment would need integration with identity and bank systems.
- No hardware acceleration (such as Telum) was used.

## Why IBM Z / LinuxONE
Disbursement is a high-volume workload where each payment must be checked and recorded exactly once, with strong security and an auditable history. The prototype runs on LinuxONE and shows the decision stays far inside a 100 ms budget.
