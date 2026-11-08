# NyayaSaathi

A simple assistant that helps normal people in India understand their options after a criminal incident, like a phone theft, an online fraud, harassment or a fight. You describe what happened in plain English (typed or spoken), and it explains possible next steps, what evidence to keep, how the police and court process works, and which laws may apply, with a link to check each one.

It is an information tool, not a lawyer. It never predicts who will win, never gives a "case score", and only shows laws it can back up from its own law notes.

## What it does

- Takes a story as text, or as an English voice recording (Sarvam speech-to-text)
- Asks follow-up questions when important details are missing
- Gives practical options with a first step for each (for example, filing an FIR)
- Lists evidence worth saving and why
- Explains the general police and court process
- Suggests possible laws (new BNS/BNSS/BSA with the old IPC/CrPC numbers), **only from retrieved references**
- Points to free legal aid (NALSA) and the 1930 cyber fraud helpline when relevant

## How it works

```
User story ──► Streamlit UI ──► FastAPI ──► 1. Retrieve laws (BM25 over laws.json)
                                            2. AI model replies in fixed JSON
                                            3. Grounding check removes any law
                                               that was not retrieved
                                        ◄── validated answer shown in sections
```

**RAG (law lookup).** `backend/data/laws.json` holds 49 short plain-English summaries of common sections from the BNS, BNSS, BSA, IT Act, POCSO, Dowry Prohibition Act and Legal Services Authorities Act. Each entry has its old IPC/CrPC equivalent, everyday keywords ("snatched", "OTP", "in-laws") and an official source link. For each message, `backend/rag.py` searches these with BM25 using everything the user has said so far. It takes the top 6 matches and always adds the FIR, police-refused-FIR and free-legal-aid entries. These go into the prompt.

**Grounding check.** The model may only cite a law by its id from the retrieved list. After the reply, `backend/service.py` drops any law that was not retrieved and takes the act, section and link from `laws.json`, not from the model. The UI shows how many suggestions were hidden.

Why BM25 and not a vector database: with ~50 entries it's instant (~0.1 ms per search), needs no extra service, and you can see exactly why something matched.

## Project structure

```
backend/
  main.py            FastAPI app: /health, /api/analyze, /api/transcribe
  service.py         prompt, AI call, response validation, grounding check, transcription
  rag.py             tokenizer + BM25 search over the law notes
  data/laws.json     law knowledge base (49 entries)
streamlit_app.py     the web page
eval/
  cases.json         20 realistic test stories with expected laws
  run_retrieval_eval.py
tests/               unit tests (contract, prompt rules, retrieval, grounding, transcription)
scripts/
  generate_raw_outputs.py   runs the app on the test inputs and saves results
raw_outputs/         unedited outputs from a real run
```

## Setup

The app works with any OpenAI-compatible chat-completions API. Copy the example env file and fill in your own values:

```bash
cp .env.example .env
```

| Variable | Required | Purpose |
|---|---|---|
| `AI_API_BASE_URL` | yes | Base URL of the chat API, e.g. `https://api.openai.com/v1` |
| `AI_API_KEY` | yes | API key for that provider |
| `AI_MODEL` | yes | Model name |
| `SARVAM_API_KEY` | no | Enables voice input via Sarvam (used first if set) |
| `SARVAM_TRANSCRIPTION_MODEL` | no | Defaults to `saarika:v2.5` |
| `AI_TRANSCRIPTION_MODEL` | no | Fallback voice model on your chat provider |

`.env` is git-ignored. Never commit real keys.

### Run with Docker

```bash
docker compose up --build
```

Open http://localhost:8501. The API runs at http://localhost:8000. Stop with `Ctrl+C`, then `docker compose down`.

### Run without Docker

Needs Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
set -a; source .env; set +a        # load your keys into the shell
uvicorn backend.main:app --reload
```

In a second terminal (same venv):

```bash
streamlit run streamlit_app.py
```

## Testing

Neither of these needs an API key.

```bash
python -m unittest discover -s tests -t .     # 10 unit tests
python -m eval.run_retrieval_eval             # retrieval quality on 20 stories
```

Current retrieval results (top 6):

| Metric | Result |
|---|---|
| At least one correct law found | 17 / 19 = 89% |
| All expected laws found | 16 / 19 = 84% |
| Recall over all expected laws | 26 / 30 = 87% |

One unit test makes the model "return" a made-up section and checks that it is removed, so the no-fake-laws rule is enforced in code.

## Raw outputs

`raw_outputs/` has unedited results from running the full app (real model) on my 20 test stories and 2 follow-up conversations. Each case file has the laws retrieved, the model's raw reply before the grounding check, and the final answer after it. See [raw_outputs/README.md](raw_outputs/README.md). To regenerate (needs `.env`):

```bash
python -m scripts.generate_raw_outputs
```

## Known limitations

- Criminal matters only, English only. Hinglish like "mera phone chura liya" isn't matched by retrieval.
- Vague stories ("someone took my stuff") can miss the right law until follow-up answers add detail.
- Civil disputes (for example a landlord keeping a deposit) can still pull in criminal sections at retrieval time. The prompt asks the model to say it's not a criminal matter.
- The law notes are my own simplified summaries, not official text, and have not been reviewed by a lawyer. Source links point to the India Code home page, not to exact sections.
- I wrote both the keywords and the eval stories, so real-world accuracy is probably lower than the numbers above.
- No chat history is saved. Refreshing the page clears it.

## Privacy and legal limits

There is no login or database. The current chat lives only in the Streamlit session. Text is sent to the configured AI provider, and voice recordings go to Sarvam (or the fallback provider). Users must tick a consent box first and are asked not to share names, addresses or phone numbers. Each provider has its own data-retention policy.

Suggested laws are possibilities to verify, not legal conclusions. Check them with a local lawyer. Free legal aid information is available from the [National Legal Services Authority](https://nalsa.gov.in/).
