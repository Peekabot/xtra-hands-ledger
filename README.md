# xtra-hands-ledger

Smallest test only. SQLite project ledger. Camera log is optional.

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

Photo + notes land in `photos/` and `events` (`kind=job_log`).
Keep iSH open or the server dies.
