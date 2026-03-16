# Værktøjer til selvkørende agent (terminal)

Kør disse kommandoer **én gang** i PowerShell (som administrator hvis nødvendigt). Efter install: **luk og åbn terminal/Cursor igen** så PATH opdateres. Derefter kan agenten køre pip, tests, git og (valgfrit) Docker uden at du skal gøre noget.

---

## Påkrævet for AI-CORE (install, test, kør)

### Git
```powershell
winget install --id Git.Git -e --source winget
```
(Efter install: genstart terminal. Så virker `git` i den shell agenten bruger.)

### Python 3.11
```powershell
winget install Python.Python.3.11 -e --source winget
```
(Efter install: genstart terminal. Så virker `py` og typisk `python`; brug `py -m pip`, `py -m uvicorn`, `py -m unittest`.)

---

## Valgfrit – Clawrunner (OpenClaw gateway)

Vi bruger **Clawrunner** ([jacobxo0/Clawrunner](https://github.com/jacobxo0/Clawrunner)) som OpenClaw gateway. Den kræver **Node.js 22+**:

```powershell
winget install -e --id OpenJS.NodeJS.22
```
(Svar Y hvis winget spørger om agreements.) Eller hent Node 22 fra https://nodejs.org/ (v22.x). Efter install: genstart terminal, så `node --version` viser v22.x.

---

## Valgfrit – Claude Code CLI (terminal via Claude)

**Claude Code** er Anthropics CLI så du kan køre `claude` i terminalen og lade Claude udføre kommandoer. Kræver **Git** (se ovenfor).

```powershell
irm https://claude.ai/install.ps1 | iex
```

Efter install: **tilføj install-stien til PATH** hvis scriptet siger det: `C:\Users\Jnkri\.local\bin` → Systemegenskaber → Miljøvariabler → Rediger bruger-PATH → Ny → indsæt stien. Genstart terminal. Tjek med `claude --version` og `claude doctor`. Kør `claude` i en projektmappe for at starte. Hvis Git Bash ikke findes automatisk:

```powershell
$env:CLAUDE_CODE_GIT_BASH_PATH="C:\Program Files\Git\bin\bash.exe"
```

---

## Valgfrit (gør agenten endnu mere selvkørende)

### Docker (lokale builds og kørsel af images)
```powershell
winget install --id Docker.DockerDesktop -e --source winget
```
(Efter install: start Docker Desktop én gang; derefter virker `docker build` og `docker run` i terminalen.)

### Railway CLI (deploy fra terminal uden at åbne browser)
```powershell
winget install --id Railway.Railway -e --source winget
```
Eller via npm (hvis Node er installeret): `npm install -g @railway/cli`  
Derefter: `railway login` én gang i terminalen. Så kan agenten køre `railway up` eller tilsvarende fra projektmappen.

---

## Tjek at alt er der

I en **ny** PowerShell (efter genstart):

```powershell
git --version
py --version
py -m pip --version
```

Valgfrit:
```powershell
docker --version
railway --version
```

Hvis alle disse svarer (uden "not recognized"), er agenten så selvkørende som muligt fra terminalen.

---

**Clawrunner status:** Når Clawrunner crasher på Railway (fx "Crashed 17 hours ago"), brug checklisten i [openclaw_installation_plan.md](openclaw_installation_plan.md) under "Hvad mangler for at få det helt op og kører" og læs Railway Deploy Logs for `[FATAL]` og `[STDERR from gateway]`. Fix sker i Clawrunner-repoet (config, ollama.models array, stderr-handling).
