# AI-assisted work log (QryptoNox Quantum Oracle Forensics)

Rules (section 10): AI assistants are permitted; assistance must be declared and results independently verified.
Tool: Claude Code (Claude Sonnet 5.5). Team: 3 members, beginners in quantum computing.

| # | Date | What the AI did | How we verified it |
|---|------|-----------------|--------------------|
| 1 | 2026-10-15 | Read the problem-statement PDF and summarised task, scoring and rubric in plain language. | Team to re-read PDF sections 3, 5, 8 and 13 against the summary. |
| 2 | 2026-10-15 | Created `.venv`, installed qiskit 2.5.2, numpy 2.5.4, scipy 1.18.1; pinned in `requirements.txt`. | `pip freeze`, version printout. |
| 3 | 2026-10-15 | Wrote `oracle_sim.py` (8 oracle families, noisy `run()` harness with query counter) and `test_sim.py`. | `test_sim.py`: section 4 example values reproduced; family properties on 50 random instances; noiseless Bernstein-Vazirani returns `a`; measured noise rates match analytic values (0.9423 vs 0.9416; 0.8509 vs 0.8508). |
| 4 | 2026-10-15 | Proposed a solving strategy (not yet implemented). | Pending: to be validated by simulation against baselines (section 9). |

Corrections made during review: removed one vacuous test (`... or True`) that the AI initially wrote.

Open items: strategy decisions must come from query results only (no hard-coded answers); final report must restate this disclosure on one page.
