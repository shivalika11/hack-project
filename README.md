# Memory Lantern

**Memory Lantern** is a quiet, local-first writing space for turning your own memories into a short remembrance. It uses an open-weight language model through [Ollama](https://ollama.com/) on your computer. No account, API key, cloud model, or third-party service is involved.

The model helps shape a note, poem, or caption from details you choose to share. It does not imitate a person's voice or claim to speak for them. The result is a draft for you to review and edit—not a recovered memory or a message from beyond.

## Run locally

1. Install [Python 3](https://www.python.org/downloads/) and [Ollama](https://ollama.com/download).
2. Start Ollama, then download a model once:

   ```sh
   ollama pull qwen2.5:3b
   ```

   The model download needs internet. After it is installed, writing drafts works locally without an internet connection.
3. From this folder, run:

   ```sh
   python app.py
   ```

4. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

Memory Lantern binds to `127.0.0.1` and sends prompts only to Ollama at `127.0.0.1:11434`. The model picker lists models already installed in Ollama. To try another, download it with `ollama pull <model-name>` and use **Refresh** in the app.

If you use another port, set `PORT` before starting the server (for example, `PORT=8080 python app.py` in a POSIX shell or `$env:PORT=8080; python app.py` in PowerShell).

## Why open and local

A remembrance can be deeply personal. Running the model on your own computer keeps the prompt out of a hosted AI service, avoids API keys and per-request fees, and still works without internet after the model is downloaded. Because the app speaks Ollama's local API and offers installed models in a picker, you can inspect the flow and switch models without rewriting the app.

Local models are not a universal upgrade: generation speed and writing quality depend on your hardware and the model you choose, and a small model may be less capable than a hosted frontier model. `qwen2.5:3b` is a convenient starting point, not the only choice. Review the model's own license and terms before using another model.

## Privacy and care

- Memory Lantern does not save your input, keep a history, or send analytics. The Python server does not log request details.
- Your text is sent to the local Ollama process only. The first model download is the only network-dependent step.
- Copy and download are explicit actions you control. A downloaded file is stored by your browser in its normal downloads location.
- The model can produce inaccurate or unexpected language. Read and edit every draft before keeping or sharing it.
- The app will not impersonate a deceased person, invent facts, or claim to channel anyone. Do not use it to create a likeness or voice.
- Día de Muertos is a living tradition with deep cultural roots. This app is not a substitute for that tradition; use only the practices and offerings that are meaningful to you.

## Tests

The app and tests use only the Python standard library:

```sh
python -m unittest -v
```

## How it works

```text
Your browser ──same-machine──> Memory Lantern (Python)
                                      │
                                      └──127.0.0.1──> Ollama ──> chosen local model
```

The browser UI is plain HTML, CSS, and JavaScript. The Python server serves those static files and proxies model discovery and generation to Ollama's local HTTP API. The only model name in the app is a suggested default; generation uses the installed model you choose.

## Challenge submission

This repository contains the project build, not a DEV entry. The Hacktoberfest Open-Source AI Challenge: Week 4 requires a DEV post tagged `hf26challenge` that shows the project and explains why open innovation matters. Submissions close October 31, 2026 at 11:59 PM PDT.
