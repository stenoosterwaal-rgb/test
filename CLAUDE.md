# ASI-Evolve — Getting Started on Your Android Phone

This guide gets you from zero to running ASI-Evolve on your Android browser in about 15 minutes. **Everything is free.**

---

## What you will need

| Thing | Cost | Time |
|---|---|---|
| Groq API key | **Free forever** | 3 min |
| Railway account | Free tier | 3 min |
| GitHub account | Free | (you have this) |

---

## Step 1 — Get a free Groq API key

1. Open your Android browser and go to **console.groq.com**
2. Tap **Sign up** and create an account (email + password)
3. Verify your email
4. Once logged in, tap **API Keys** in the left menu
5. Tap **Create API Key** → give it a name (e.g. "asi-evolve") → **Submit**
6. **Copy the key** — it starts with `gsk_...`
   > Keep this key private. Never share it publicly.

---

## Step 2 — Create a Railway account

1. Go to **railway.app** in your browser
2. Tap **Login** → **Login with GitHub**
3. Authorise Railway to access your GitHub account

---

## Step 3 — Deploy the app

1. In Railway, tap **New Project**
2. Tap **Deploy from GitHub repo**
3. Select **stenoosterwaal-rgb/test**
4. Railway will auto-detect the `Dockerfile` and start building
   > The first build takes about 3–5 minutes (it installs AI models)

---

## Step 4 — Add your API key

1. In your Railway project, tap the service card
2. Tap **Variables** (or **Settings → Variables**)
3. Tap **New Variable**
4. Set:
   - **Name**: `GROQ_API_KEY`
   - **Value**: paste your `gsk_...` key
5. Tap **Add** — Railway will redeploy automatically

---

## Step 5 — Open the app

1. In Railway, tap your service → **Settings → Networking**
2. Tap **Generate Domain** if no domain is shown yet
3. Copy the `.railway.app` URL
4. Open it in your Android browser
5. You should see a **green dot** next to "Groq key set" in the top-right corner

---

## Step 6 — Run your first experiment

1. Use the slider to choose how many evolution steps to run (10 is a good start)
2. Tap **▶ Start Demo**
3. Watch the live log — the AI is designing, testing, and improving circle-packing algorithms
4. After all steps complete, the **Best Result** panel shows the score and the winning code

> **What is the demo doing?**
> It tries to pack 26 circles into a 1×1 square to maximise their total radius.
> The world record (AlphaEvolve, 2025) is **2.635**. ASI-Evolve tries to beat it.

---

## Tips

- **Runs are saved** — if you stop and restart, it picks up where it left off
- **More steps = better results** — try 30–50 steps for serious improvement
- **Cost** — Groq is **completely free** on the free tier. No credit card needed.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Red "No API key" dot | Add `GROQ_API_KEY` in Railway Variables |
| "A run is already in progress" | Tap **■ Stop**, wait a moment, then start again |
| App not loading | Check Railway → Deployments for build errors |
| Build fails | Make sure you're deploying from the `claude/new-session-IdFse` branch |
