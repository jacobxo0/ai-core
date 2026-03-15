# Deployment plan: AI-CORE + OpenClaw på Railway / server

Komplet plan for at køre AI-CORE og OpenClaw enten på Railway eller på en Windows-server. OpenClaw/Clawrunner-detaljer (env, crash-fix) står i [openclaw-railway-reference.md](openclaw-railway-reference.md).

---

## 1. Overblik

- **AI-CORE** (dette repo): Én Railway-service; eksponerer `POST /command`, `GET /tools`.
- **OpenClaw/Clawrunner:** Enten (A) anden Railway-service (Clawrunner-repo, Linux), eller (B) Windows-server med `irm https://openclaw.ai/install.ps1 | iex`. Claw kører på serveren, ikke lokalt.
- **Forbindelse:** OpenClaw/Clawrunner kalder AI-CORE's `POST /command` (og evt. `GET /tools`).

---

## 2. Forudsætninger

- **GitHub-repo** for AI-CORE tilknyttet Railway.
- **Railway-konto** (evt. betalt plan for mere RAM/CPU).
- **Valg af OpenClaw-miljø:**
  - **Kun Railway:** OpenClaw/Clawrunner som anden Railway-service (Linux; deploy fra Clawrunner-repo/Docker).
  - **Windows-server:** En VPS eller maskine med Windows. Kør `install.ps1` på serveren – ikke lokalt.

---

## 3. Del A: AI-CORE klar til Railway

I dette repo (implementeret):

1. **requirements.txt** – `fastapi`, `uvicorn`, `pydantic` med versioner.
2. **Dockerfile** – `python:3.11-slim`, start: `uvicorn apps.orchestrator.main:app --host 0.0.0.0 --port ${PORT:-8000}`. Railway sætter `PORT` ved runtime.
3. **.dockerignore** – udelukker .git, venv, data/, tests så image forbliver lille.
4. **data/** er ephemeral på Railway medmindre I tilknytter Volume.

---

## 4. Del B: Deploy AI-CORE på Railway

1. Nyt Service i Railway; connect AI-CORE's GitHub-repo.
2. Root directory: repo root. Build: Dockerfile eller Nixpacks med start command.
3. Efter deploy: notér public URL (fx `https://ai-core-xxx.railway.app`) som **AI_CORE_URL**.
4. Tjek: `GET /`, `GET /tools`, `POST /command` med `{"command":"echo","arguments":{"message":"hi"}}`.

---

## 5. Del C: OpenClaw på server (flere veje)

OpenClaw (Clawrunner) kan installeres eller deployes via **Railway**, **GitHub** (kilde + deploy/CI), eller **Docker** (build og kør image lokalt/andre hosts). Fuld, nøje gennemgang af alle tre: [openclaw_installation_plan.md](openclaw_installation_plan.md).

| Leveringsvej | Beskrivelse |
|--------------|-------------|
| **Railway** | Clawrunner som Railway-service; build fra Dockerfile, start railway-start.sh, env i Railway Variables. |
| **GitHub** | Kilde er Clawrunner-repo på GitHub; deploy ved Railway connected til repo (build ved push) eller GitHub Actions der bygger image. Secrets/env ikke i repo. |
| **Docker** | Byg image i Clawrunner-repo med `docker build`; kør med `docker run` og env vars. Samme Dockerfile som Railway; brugbar til lokal test eller egen VPS. |

### Vej 1: OpenClaw på Windows-server (install.ps1)

På Windows-serveren (fx via RDP): Åbn PowerShell og kør:

```powershell
irm https://openclaw.ai/install.ps1 | iex
```

Eller fra andet shell: `powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://openclaw.ai/install.ps1 | iex"`. Følg prompts; sæt derefter **AI_CORE_URL** til AI-CORE's Railway-URL i OpenClaw's config eller miljøvariabler. Sørg for at serveren kan lave udgående kald til Railway.

### Vej 2: Clawrunner kun på Railway (Linux)

- Byg med **Dockerfile**; start = `bash scripts/railway-start.sh`.
- **Env vars:** Se [openclaw-railway-reference.md](openclaw-railway-reference.md) for fuld liste. Mindst: `OPENCLAW_GATEWAY_TOKEN`, `TELEGRAM_BOT_TOKEN` (hvis Telegram), `PORT` (sættes af Railway). Ved AI-CORE-integration: `AI_CORE_URL` = AI-CORE's Railway-URL.
- **Fejlsøgning:** Token mangler, template mangler, gateway exit 1 (JSON/Ollama), CRLF, OOM – se [openclaw-railway-reference.md](openclaw-railway-reference.md). Læs Railway Deploy Logs for `[FATAL]` og `[STDERR from gateway]`.
- **Telegram webhook:** Sæt til `https://<CLAWRUNNER_DOMAIN>/telegram`. Generate Domain i Railway → Networking.

---

## 6. AI-CORE som backend

- AI-CORE deployes først (Del B); notér **AI_CORE_URL**.
- I Clawrunner/OpenClaw: sæt `AI_CORE_URL` i config eller Railway Variables.
- I Clawrunner-koden: tool-execution skal kalde `POST {AI_CORE_URL}/command` med body `{"command": "<tool>", "arguments": {...}}`. Konkrete kodeændringer sker i Clawrunner-repoet, ikke i AI-CORE.

---

## 7. Anbefalet rækkefølge

1. Tilføj `requirements.txt` og Dockerfile i AI-CORE (implementeret); test lokalt: `uvicorn apps.orchestrator.main:app --host 0.0.0.0 --port 8000`.
2. Deploy AI-CORE til Railway; verificer `/`, `/tools`, `/command`.
3. **Enten (Vej 1):** På Windows-server: kør `irm https://openclaw.ai/install.ps1 | iex`, sæt `AI_CORE_URL`, start OpenClaw. **Eller (Vej 2):** Deploy Clawrunner på Railway, sæt `AI_CORE_URL`, fix crash og hold deployment kørende.
4. Test fra OpenClaw/Clawrunner: kør et command mod AI-CORE og bekræft at ToolResult kommer tilbage.

---

## 8. Dokumentation / notér

Notér her (eller i et separat runbook): Railway URL(s), valgt OpenClaw-vej (Windows-server eller kun Railway), og de env vars I brugte (fx `AI_CORE_URL`, `OPENCLAW_GATEWAY_TOKEN`, `TELEGRAM_BOT_TOKEN`). Notér også hvilken **Railway region** (fx us-west2) og evt. **Hetzner datacenter** I bruger, så opsætning kan gentages eller fejles systematisk.

---

## 9. Kort opsummering

| Element | Handling |
|---------|----------|
| AI-CORE deploy | requirements.txt + Dockerfile; deploy repo til Railway; brug PORT og 0.0.0.0. |
| AI_CORE_URL | Notér Railway-URL; brug den i OpenClaw/Clawrunner. |
| OpenClaw – **Railway** | Clawrunner som Railway-service; Dockerfile + railway-start.sh; env i Variables. Se [openclaw_installation_plan.md](openclaw_installation_plan.md). |
| OpenClaw – **GitHub** | Clawrunner-repo på GitHub; deploy via Railway connect eller GitHub Actions. Secrets ikke i repo. Se [openclaw_installation_plan.md](openclaw_installation_plan.md). |
| OpenClaw – **Docker** | `docker build` i Clawrunner-repo; `docker run` med env. Samme image som Railway. Se [openclaw_installation_plan.md](openclaw_installation_plan.md). |
| OpenClaw på server (Windows) | På Windows-server: kør install.ps1 fra openclaw.ai; sæt AI_CORE_URL. |
| Lokal Claw | Undladt; alt kører på Railway og/eller Windows-server. |

---

## 10. Fælles checkliste

**AI-CORE**

- [ ] requirements.txt (og evt. Dockerfile) med `--host 0.0.0.0` og `$PORT`.
- [ ] Deploy til Railway; notér URL.
- [ ] Test `GET /`, `GET /tools`, `POST /command`.

**Clawrunner**

- [ ] Dockerfile + railway-start.sh; env vars (OPENCLAW_GATEWAY_TOKEN, TELEGRAM_*, evt. OLLAMA_*).
- [ ] Generate Domain; Telegram webhook til domænet.
- [ ] Ved integration: `AI_CORE_URL` sat; Clawrunner sender tool-kald til `POST /command`.

**Selvforbedrende cyklus (senere)**

- Scheduler i AI-CORE; analyse-tool + review-lag; kun godkendte handlinger køres. Se arkitektur-roadmap.
