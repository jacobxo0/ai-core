# OpenClaw / Clawrunner på Railway – reference

Udtræk fra OpenClaw-materiale (D:\.openclaw) til Railway-deploy, env vars og fejlsøgning. Bruges sammen med [deployment_plan.md](deployment_plan.md). Samme Dockerfile og env-krav bruges ved ren Docker-kørsel (lokalt eller på egen VPS); GitHub er kilde til både Railway-deploy og lokale Docker-builds. Fuld installationsplan for Railway, GitHub og Docker: [openclaw_installation_plan.md](openclaw_installation_plan.md).

---

## 1. Hvad der kører på Railway (Clawrunner)

- **Dockerfile:** `node:22-bookworm-slim`, `npm install --omit=dev`, `CMD ["bash", "scripts/railway-start.sh"]`. Port 18789 eksponeret; Railway sætter `PORT`.
- **Start-flow (railway-start.sh):**
  - Sæt `PORT` fra env (default 18789).
  - Kræv `OPENCLAW_GATEWAY_TOKEN`.
  - Byg `openclaw.json` fra `openclaw.railway.example.json` ved at erstatte `${VAR}` med env (Node-script).
  - Opret `workspace`, `cron`, `.openclaw`-config.
  - `NODE_OPTIONS="--max-old-space-size=1024"` og `--unhandled-rejections=warn`.
  - Kør `npx openclaw gateway --port $PORT --allow-unconfigured`; **stderr** fanges i `gateway.stderr` og printes ved exit.
  - Ved exit: `[FATAL] Gateway exited with code N` + indhold af stderr.

Crash kommer typisk **efter** "Starting OpenClaw gateway" – dvs. selve gateway-processen eller et plugin fejler.

---

## 2. Env vars (Railway Variables)

| Variabel | Påkrævet | Brug |
|----------|----------|------|
| `OPENCLAW_GATEWAY_TOKEN` | Ja | Gateway auth; samme som `gateway.auth.token` i openclaw.json. |
| `TELEGRAM_BOT_TOKEN` | Ja (hvis Telegram) | Bot-token fra BotFather. |
| `TELEGRAM_GROUP_ALLOW_FROM` | Anbefalet | JSON-array med tilladte user-id'er, fx `["8572521981"]`. |
| `PORT` | Sættes af Railway | Bruges af railway-start.sh. |
| `OLLAMA_BASE_URL` | Ja (hvis Ollama) | Fx `http://<HETZNER-IP>:11434`. Uden den bruger template OpenAI som primary. |
| `OLLAMA_API_KEY` | Ja (hvis Ollama) | Fx `ollama-vps`. |
| `BRAVE_API_KEY` | Anbefalet | Web search. |
| `GITHUB_TOKEN` / `GITHUB_USERNAME` | Valgfrit | Til GitHub-skill. |
| `AI_CORE_URL` | Ved AI-CORE-integration | Fx `https://ai-core-xxx.railway.app`. Bruges af Clawrunner til `POST /command` for tool-execution. Skal tilføjes i config og kode i Clawrunner-repoet. |

---

## 3. Crash-fejl og fix

| Fejl i logs | Årsag | Fix |
|-------------|--------|-----|
| `OPENCLAW_GATEWAY_TOKEN ikke sat` | Manglende variabel | Railway Variables → tilføj `OPENCLAW_GATEWAY_TOKEN`. Redeploy. |
| `openclaw.railway.example.json ikke fundet` | Template mangler i build | Tjek at filen er i repo og inkluderet i Docker COPY. |
| `Gateway exited with code 1` (efter start) | Ugyldig openclaw.json eller plugin (Telegram/Ollama) | Tjek at env-substitution giver gyldig JSON. Hvis `OLLAMA_BASE_URL` sat: Railway skal kunne nå Ollama; kan den ikke, fjern midlertidigt `OLLAMA_BASE_URL` og brug OpenAI som primary. |
| CRLF i scripts (`\r: command not found`) | Windows line endings i .sh | `.gitattributes` med `*.sh text eol=lf` og evt. `git add --renormalize .`. |
| JavaScript heap out of memory | For lidt RAM | Sæt `NODE_OPTIONS=--max-old-space-size=1536` eller øg Service memory i Railway. |

Stderr fanges i railway-start.sh (gateway.stderr printes ved exit) – læs **Railway Deploy Logs** for `[FATAL]` og `[STDERR from gateway]`.

---

## 4. Config-template (openclaw.railway.example.json)

- Modeller: `ollama` med `baseUrl: ${OLLAMA_BASE_URL}`; hvis tom fjernes Ollama og primary sættes til `openai/gpt-5.1-codex`.
- Gateway: port fra env, auth `token: ${OPENCLAW_GATEWAY_TOKEN}`.
- Telegram: `botToken`, `allowFrom`/`groupAllowFrom` fra env.
- Tools: Brave search med `${BRAVE_API_KEY}`. Skills: github, notion med env.

**AI-CORE:** Tilføj evt. "tools"/"backend"-felt med `AI_CORE_URL` og brug det i Clawrunner til at sende tool-kald til AI-CORE's `POST /command`.
