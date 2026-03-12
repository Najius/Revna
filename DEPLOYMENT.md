# Revna Backend Deployment

## Architecture

```
Garmin/Wearable → Terra API → Revna Backend (FastAPI) → Telegram Bot
                                    ↓
                              Claude AI (analysis)
                                    ↓
                              PostgreSQL (storage)
```

## Prerequisites

1. **Terra API** - Create account at https://tryterra.co
2. **Telegram Bot** - Create via @BotFather at https://t.me/BotFather
3. **Anthropic API** - Get key at https://console.anthropic.com

## Deploy to Railway

### 1. Create Project

1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Select the Revna repository
4. Railway will auto-detect the `railway.toml` configuration

### 2. Add PostgreSQL

1. In your Railway project, click "New" → "Database" → "PostgreSQL"
2. Railway automatically sets `DATABASE_URL`

### 3. Configure Environment Variables

In Railway Dashboard → Variables, add:

```env
# App
APP_ENV=production
APP_SECRET_KEY=<generate-random-string>
LOG_LEVEL=INFO

# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_WEBHOOK_URL=https://<your-app>.railway.app/webhooks/telegram

# Terra API (wearables)
TERRA_API_KEY=<from-terra-dashboard>
TERRA_DEV_ID=<from-terra-dashboard>
TERRA_WEBHOOK_SECRET=<from-terra-dashboard>
```

### 4. Deploy

Railway deploys automatically. The startup command runs:
1. `alembic upgrade head` - Database migrations
2. `uvicorn backend.main:app` - Start server

### 5. Configure Webhooks

After deployment, configure the external services:

**Telegram Webhook:**
```bash
# Option A: Call the API endpoint
curl -X POST https://<your-app>.railway.app/setup/telegram-webhook

# Option B: Manual setup
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-app>.railway.app/webhooks/telegram"
```

**Terra Webhook:**
1. Go to Terra Dashboard → Webhooks
2. Add webhook URL: `https://<your-app>.railway.app/webhooks/terra`
3. Copy the webhook secret to `TERRA_WEBHOOK_SECRET`

## Verify Deployment

1. **Health check:**
   ```bash
   curl https://<your-app>.railway.app/health
   # → {"status": "ok", "service": "revna"}
   ```

2. **Telegram bot:**
   - Message `/start` to your bot
   - Should receive welcome message

3. **Connect wearable:**
   - Message `/connect` to bot
   - Click the Terra widget link
   - Authorize your Garmin/Apple/etc

4. **Check logs:**
   - Railway Dashboard → Deployments → View Logs

## Telegram Commands

- `/start` - Create account and get welcome message
- `/connect` - Get link to connect wearable device

## Scheduled Jobs

The backend runs these automatically:

| Time | Job |
|------|-----|
| 07:30 | Morning health report |
| 07:45 | Morning check-in |
| 11:00, 14:00, 17:00, 20:00 | Health monitoring |
| 18:00 | Evening steps summary |
| 20:00 | Evening report |
| 22:00 | Evening check-in |
| Every 30min | Wearable data sync |
| 03:00 | Daily system audit |

## Troubleshooting

**Telegram webhook not working:**
- Check `TELEGRAM_BOT_TOKEN` is correct
- Verify webhook URL is HTTPS
- Call `/setup/telegram-webhook` endpoint

**Terra data not syncing:**
- Verify `TERRA_API_KEY` and `TERRA_DEV_ID`
- Check Terra webhook URL in dashboard
- Ensure `TERRA_WEBHOOK_SECRET` matches

**No AI responses:**
- Check `ANTHROPIC_API_KEY` is valid
- Check Claude API quota/limits

## Alternative: Deploy to Render

1. Create account at https://render.com
2. New → Web Service → Connect GitHub repo
3. Set build command: `pip install -e .`
4. Set start command: `alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add PostgreSQL database
6. Configure environment variables (same as Railway)
