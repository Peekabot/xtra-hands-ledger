# xtra-hands-ledger

Smallest test only. SQLite project ledger. No Lupa, no HTTP.

## iSH pull and run

```bash
apk add git sqlite python3
cd /root
git clone https://github.com/Peekabot/xtra-hands-ledger.git
cd xtra-hands-ledger
chmod +x run_test.sh
./run_test.sh
```

Expected last lines: `PERSIST OK` then `CLOSE PREDICATE OK`.

Then force-quit iSH, reopen:

```bash
sqlite3 /root/xtra-hands-ledger/projects.db 'SELECT name,status FROM projects; SELECT name,status FROM tasks;'
```

If those rows are still there, persistence works. Stop. Do not add Lupa yet.
