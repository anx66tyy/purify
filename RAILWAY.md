# PURIFY on Railway

This project is ready to deploy on Railway as a Python worker service.

## 1) Create the project

- Go to Railway
- New Project -> Deploy from GitHub Repo
- Select `anx66tyy/purify`

## 2) Add environment variables

In the Railway Variables tab, add:

```env
DISCORD_TOKEN=your_discord_token_here
DATABASE_URL=sqlite:///data/purify.db
BOT_PREFIX=.
OWNER_IDS=your_owner_discord_id
LOG_LEVEL=INFO
ENABLE_TTS=true
PYTHON_ENV=production
```

## 3) Deploy

Railway will build using the included `Dockerfile` and `railway.json`.

## 4) Verify

Once deployed, check the Railway logs for startup messages and ensure the bot connects to Discord.

## Notes

- The bot does not expose a web port, so it should run as a standard Python service.
- Database storage is SQLite by default, which is suitable for lightweight deployment and testing.
- For more production-scale deployments, you can later switch the database backend to PostgreSQL or MongoDB.
