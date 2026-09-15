# xtra-hands-ledger

SQLite job ledger for Xtra Hands. Camera log and bid ingest are optional extras.

## Already cloned?

```bash
cd /root/xtra-hands-ledger
git pull
```

Do not clone a second copy.

## Ledger test

```bash
apk add git sqlite python3
cd /root/xtra-hands-ledger
chmod +x run_test.sh
./run_test.sh
```

## Camera job log (iSH foreground + Safari)

```bash
cd /root/xtra-hands-ledger
python3 cam_server.py
```

Safari: `http://127.0.0.1:8000/`

## Bid watcher

The scraper lives in `Peekabot/xtra-hands-bid-triage`. This repo only records new bids.

```bash
# optional: produce JSON
cd /root/xtra-hands-bid-triage && python3 scripts/bid_triage.py

# ingest into ledger (uses sample if no JSON)
cd /root/xtra-hands-ledger
git pull
python3 watch_bids.py
python3 watch_bids.py   # second run should print: no new bids
sqlite3 projects.db 'SELECT id,name,status FROM projects; SELECT url,decision,project_id FROM bids;'
```
