# Clothing Finder — Getting Started on Your Android Phone

Upload a photo or screenshot of a clothing item, and the app uses a vision AI
to identify the brand/type/colour and then helps you find that exact item on
**Vinted** and on the original seller's site (via Google Lens and Google
Shopping).

This guide gets you from zero to running on your Android browser in about
15 minutes. **Everything is free.**

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
5. Tap **Create API Key** → give it a name (e.g. "clothing-finder") → **Submit**
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
   > The first build takes about 1–2 minutes.

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

## Step 6 — Find a piece of clothing

1. Tap the upload area and either **choose a photo** from your gallery or
   **take a new one** with your camera.
2. Tap **Find this item**.
3. After a few seconds you get:
   - **Detected item** — brand guess, item type, colour, distinctive
     features, and a confidence badge.
   - **Find this item** — buttons to search **Vinted**, **Google Lens**
     (reverse image search, best for finding the exact original listing),
     and **Google Shopping**.
   - **Top Vinted matches** — when Vinted is reachable, a small grid of
     listings appears inline.

> **What's happening behind the scenes?**
> The image is sent to a free Groq vision model (Llama 4 Scout) which
> extracts a structured description. The app then builds smart search
> URLs and tries to pull a few Vinted listings directly.

---

## Tips

- **Google Lens** is usually the strongest link for finding the *exact*
  product page on the original seller's site — open it first.
- **Vinted** searches work best when the brand is detected. Edit the
  search on Vinted if the auto-generated query is too narrow.
- **Cost** — Groq is **completely free** on the free tier. No credit
  card needed.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Red "No API key" dot | Add `GROQ_API_KEY` in Railway Variables |
| "Vision model failed" | Re-try; if persistent, your Groq key may be invalid |
| No Vinted thumbnails | Vinted may be blocking the server — the search-link buttons still work |
| App not loading | Check Railway → Deployments for build errors |
| "Image is larger than 8 MB" | Take a smaller photo or compress before uploading |
