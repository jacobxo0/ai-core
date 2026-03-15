# OpenClaw (Clawrunner) installation – Railway, GitHub, Docker

Én nøje plan for at installere eller deploye OpenClaw (Clawrunner) med tre leveringsveje. Clawrunner-koden ligger i et andet repo (fx `jacobxo0/Clawrunner`); denne doc beskriver kun hvordan man installerer/deployer den.

Fuld env-tabel og crash-fejlsøgning: [openclaw-railway-reference.md](openclaw-railway-reference.md).

---

## Overblik

| Vej | Hvornår | Kort beskrivelse |
|-----|---------|-------------------|
| **Railway** | Du vil køre OpenClaw i skyen uden egen server | Railway-service der bygger fra Clawrunner-repos Dockerfile og kører `railway-start.sh`. Env vars sættes i Railway Variables. |
| **GitHub** | Kilde og CI/deploy | Clawrunner-repo på GitHub. Deploy sker enten ved at Railway er forbundet til repo (build ved push) eller via GitHub Actions der bygger Docker-image. Secrets/env ligger ikke i repo. |
| **Docker** | Lokal test, egen VPS, eller samme image som Railway | Byg image i Clawrunner-repo med `docker build`; kør med `docker run` og env vars. Samme Dockerfile og env-krav som Railway. |

Du kan bruge én vej eller kombinere (fx GitHub som kilde, Railway som deploy; eller Docker lokalt og Railway i prod).

---

## Spor 1 – Railway

1. **Kilde:** Clawrunner-repo på GitHub (fx `jacobxo0/Clawrunner`), branch fx `main`.
2. **Railway:** Nyt projekt eller nyt service → **Deploy from GitHub repo** → vælg Clawrunner-repo.
3. **Build:** Root directory = repo root. Railway bruger **Dockerfile** (node:22-bookworm-slim, CMD `bash scripts/railway-start.sh`). Port eksponeret; Railway sætter `PORT`.
4. **Variables:** I Railway → Clawrunner-service → **Variables** sæt mindst:
   - `OPENCLAW_GATEWAY_TOKEN` (påkrævet)
   - `TELEGRAM_BOT_TOKEN` (hvis Telegram)
   - `TELEGRAM_GROUP_ALLOW_FROM` (anbefalet, JSON-array)
   - `PORT` sættes af Railway
   - Ved AI-CORE: `AI_CORE_URL` = AI-CORE's public URL
   - Ved Ollama: `OLLAMA_BASE_URL`, `OLLAMA_API_KEY`
   - Fuld liste: [openclaw-railway-reference.md](openclaw-railway-reference.md).
5. **Domain:** Generate Domain i Railway → Networking; notér URL.
6. **Telegram:** Sæt webhook til `https://<CLAWRUNNER_DOMAIN>/telegram`.

Fejlsøgning (token mangler, gateway exit 1, CRLF, OOM): [openclaw-railway-reference.md](openclaw-railway-reference.md). Læs Railway Deploy Logs for `[FATAL]` og `[STDERR from gateway]`.

---

## Spor 2 – GitHub

1. **Kilde:** Clawrunner-repo på GitHub. Repo skal indeholde:
   - `Dockerfile` (node:22-bookworm-slim, CMD railway-start.sh)
   - `scripts/railway-start.sh`
   - `openclaw.railway.example.json`
   - `.gitattributes` med `*.sh text eol=lf` så scripts har LF.
2. **Deploy-variant A – Railway forbundet til GitHub:** I Railway vælger du "Deploy from GitHub repo". Ved hvert push til den valgte branch bygger Railway automatisk. Ingen ekstra filer i repo.
3. **Deploy-variant B – GitHub Actions:** Opret fx `.github/workflows/build.yml` i Clawrunner-repo der ved push bygger Docker-image (og evt. pusher til et registry eller trigger Railway). Env vars og secrets **aldrig** i repo; brug GitHub Secrets eller Railway Variables.
4. **Secrets/env:** Altid Railway Variables eller GitHub Secrets; ikke committet i repo.

---

## Spor 3 – Docker

1. **Clone:** `git clone <clawrunner-repo-url>` og `cd` ind i repo root.
2. **Build:** `docker build -t clawrunner .` (fra mappen hvor Dockerfile ligger).
3. **Run:**  
   `docker run -p 18789:18789 -e PORT=18789 -e OPENCLAW_GATEWAY_TOKEN=<token> -e TELEGRAM_BOT_TOKEN=<token> ... clawrunner`  
   Tilføj øvrige env vars efter behov. Fuld liste: [openclaw-railway-reference.md](openclaw-railway-reference.md).
4. **AI-CORE:** Sæt `-e AI_CORE_URL=https://ai-core-xxx.railway.app` (eller din AI-CORE-URL). Clawrunner skal i koden kalde `POST {AI_CORE_URL}/command`.
5. **Evt. docker-compose:** Opret `docker-compose.yml` med `build: .`, `ports: ["18789:18789"]`, og `environment` eller `env_file` til de påkrævede variabler.

Eksempel `docker run` (minimal):

```bash
docker run -p 18789:18789 \
  -e PORT=18789 \
  -e OPENCLAW_GATEWAY_TOKEN=your-token \
  -e AI_CORE_URL=https://ai-core-xxx.railway.app \
  clawrunner
```

---

## Fælles krav

- **openclaw.railway.example.json** skal findes i repo og inkluderes i Docker-image (Dockerfile COPY).
- **Scripts:** Alle `*.sh` skal have LF (Unix line endings). Brug `.gitattributes` med `*.sh text eol=lf` og evt. `git add --renormalize .`.
- **Fejlsøgning:** [openclaw-railway-reference.md](openclaw-railway-reference.md) – FATAL, stderr, CRLF, OOM, gateway exit 1.
- **AI_CORE_URL:** Ved integration med AI-CORE skal variablen sættes (Railway Variables, Docker env, eller GitHub Secrets) og Clawrunner-koden skal læse den og kalde `POST {AI_CORE_URL}/command` med body `{"command": "<tool>", "arguments": {...}}`.

---

## Hvad mangler for at få det helt op og kører på serveren

Checkliste for at hele kæden er oppe (AI-CORE + Clawrunner + Telegram). **Telegram-variabler** (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_GROUP_ALLOW_FROM`) antages sat i Railway Variables eller env.

| # | Krav | Tjek / handling |
|---|------|------------------|
| 1 | **AI-CORE kører** | AI-CORE deployet på Railway (eller anden host). `GET /` returnerer `{"status":"AI core running"}`. Notér **AI_CORE_URL** (fx `https://ai-core-xxx.railway.app`). |
| 2 | **Clawrunner-variabler** | `OPENCLAW_GATEWAY_TOKEN` sat. `TELEGRAM_BOT_TOKEN` og evt. `TELEGRAM_GROUP_ALLOW_FROM` sat (du har disse). **AI_CORE_URL** sat til AI-CORE's URL fra trin 1. |
| 3 | **Clawrunner crasher ikke** | Gateway skal blive kørende. Hvis den exits med code 1: tjek Railway Deploy Logs for `[STDERR from gateway]`. Typiske årsager: ugyldig `openclaw.json` efter env-substitution (fx `models.providers.ollama.models` skal være array, ikke undefined), eller Ollama ikke tilgængelig – fjern midlertidigt `OLLAMA_BASE_URL` og brug OpenAI som primary indtil gateway er stabil. |
| 4 | **Domain til Clawrunner** | I Railway → Clawrunner-service → **Networking** → **Generate Domain**. Notér URL (fx `https://clawrunner-xxx.up.railway.app`). |
| 5 | **Telegram webhook** | Sæt webhook til Clawrunner-domænet: `https://<CLAWRUNNER_DOMAIN>/telegram`. Kan gøres via Telegram API (`setWebhook`) eller BotFather/andre værktøjer. Uden dette når beskeder ikke Clawrunner. |
| 6 | **Clawrunner kalder AI-CORE** | I Clawrunner-repoet skal tool-execution læse `AI_CORE_URL` og kalde `POST {AI_CORE_URL}/command` med `{"command": "<tool>", "arguments": {...}}`. Hvis denne integration ikke er implementeret endnu, skal den tilføjes i Clawrunner-koden. |
| 7 | **End-to-end test** | Send en besked i Telegram der trigger et tool-kald; bekræft at Clawrunner ringer til AI-CORE og at svar kommer tilbage (fx via logs eller Telegram-svar). |

**Kort:** Med Telegram-variabler sat mangler ofte: (2) **AI_CORE_URL** i Clawrunner, (3) stabil gateway (fx fix af config/ollama), (4) domain genereret, (5) webhook sat til det domain, (6) kode i Clawrunner der faktisk kalder `POST /command`. Brug listen ovenfor som runbook indtil alt er grønt.

---

## Se også

- [deployment_plan.md](deployment_plan.md) – overordnet AI-CORE + OpenClaw flow.
- [openclaw-railway-reference.md](openclaw-railway-reference.md) – env-tabel, crash-fix, config-template.
