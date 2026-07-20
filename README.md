# Price Tracker

Automatically checks a list of product pages every hour and sends a
Discord notification when a price changes or a sale is detected.
Runs entirely on GitHub Actions — no computer needs to stay on.

## Files

| File | Purpose |
|---|---|
| `tracker.py` | Fetches each URL, extracts price, compares to history, sends alerts |
| `urls.txt` | List of product URLs to track (one per line) |
| `requirements.txt` | Python dependencies |
| `.github/workflows/check_price.yml` | Runs `tracker.py` every hour via GitHub Actions |
| `data/price_history.json` | Stores last known price + log per URL (auto-updated) |

## Setup

### 1. Add your Discord webhook secret (done ✅)
Settings → Secrets and variables → Actions → `DISCORD_WEBHOOK`

### 2. Add product URLs
Edit `urls.txt` and add one product page URL per line.

### 3. Enable Actions (if not already)
Actions tab → if prompted, click "I understand my workflows, go ahead and enable them".

### 4. Test it manually
Actions tab → **Check Product Prices** workflow → **Run workflow** button.

### 5. Let it run
From here it runs automatically every hour.

## Notes & limitations

- **Site markup changes**: retailers change their HTML periodically. If a
  price stops being detected, check the Action's log — "Could not find a
  price on the page" means the extraction logic needs a small tweak.
- **Anti-bot protection**: some sites may block simple automated requests.
- **Price history**: stored in `data/price_history.json`, committed back
  to the repo automatically after each run.
