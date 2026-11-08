# Raw outputs

Unedited outputs from running NyayaSaathi on my own test inputs. Everything here is written by `scripts/generate_raw_outputs.py`. I did not change anything by hand.

## Inputs

- **20 single-message stories** from `eval/cases.json`: theft, snatching, UPI/OTP fraud, stalking, dowry cruelty, assault, threats, rent fraud, police refusing an FIR, fear of false arrest, workplace harassment, hacked WhatsApp, sextortion, breach of trust, hit-and-run, child abuse, plus three hard ones (a Hinglish story, a vague story, and a civil landlord dispute).
- **2 follow-up conversations** (cases 21 and 22). The user answers in a second message, which shows the clarifying-question flow and how later answers change what laws are retrieved.

## Files

| File | What it contains |
|---|---|
| `cases/NN_<name>.json` | For each turn: the user message, the laws retrieved (id + BM25 score), `model_raw_reply` (exactly what the AI returned, **before** my grounding check) and `final_output` (what the app shows, **after** the check). If a call failed, the error is saved instead. |
| `summary.md` | One row per case: issue type, laws cited, how many citations were dropped, and the laws I expected. Generated from the case files. |
| `retrieval_eval.txt` | Output of `python -m eval.run_retrieval_eval` |
| `unit_tests.txt` | Output of the unit tests |

Comparing `model_raw_reply.possible_laws` with `final_output.possible_laws` shows the grounding check at work. `dropped_citations` counts laws the model mentioned that were not in the retrieved list.

## Regenerate

```bash
cp .env.example .env      # add your keys
python -m scripts.generate_raw_outputs
```

Model outputs are not deterministic, so a rerun will give slightly different wording.
