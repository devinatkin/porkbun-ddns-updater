# Porkbun DDNS Updater (with a basic dashboard)

This is a quick tool to keep some local/self-hosted services accessible when using dynamic IPs. It updates Porkbun DNS records to match your current public IP and gives you a simple Flask web page to see what’s going on.

Not fancy, just does the job. (Made for my needs with ChatGPT helping to write stuff, so expect AI slop levels of code)

---

## What it does

- Checks your public IP every few minutes
- Updates Porkbun A records for a list of subdomains
- Creates records if they’re missing
- Shows a basic web dashboard at `http://localhost:8080`

---

## Getting started

### Clone this repo

```bash
git clone https://github.com/devinatkin/ddns-flask.git
cd ddns-flask
```

### Set up your config

Edit `app/config.json`:

```json
{
  "apikey": "your-porkbun-api-key",
  "secretapikey": "your-secret-api-key",
  "endpoint": "https://api.porkbun.com/api/json/v3"
}
```

Put the domain names you want to update in `app/ddns_addresses.txt`, one per line:

```
home.example.com
status.example.com
whatever.example.net
```

---

## Docker usage

### Build the image

```bash
docker build -t ddns-flask .
```

### Run the container

```bash
docker run -d --name ddns-flask \
  -p 8080:8080 \
  -v $(pwd)/app/config.json:/app/config.json \
  -v $(pwd)/app/ddns_addresses.txt:/app/ddns_addresses.txt \
  ddns-flask
```

Or use Docker Compose:

```bash
docker compose up -d
```

---

## Access the dashboard

Once it’s running, open your browser to:

```
http://<your-pi-or-server-ip>:8080
```

You’ll see your tracked domains, their update status, and whether anything failed.

---

## Notes

- Only works with Porkbun’s API
- Assumes all records are A (IPv4)
- Dashboard is basic and not secured — don’t expose it publicly
- Logs show up in the container output

---

## License

MIT. No warranties. If it breaks, you get to keep both pieces.

