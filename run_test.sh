#!/bin/sh
set -e
cd "$(dirname "$0")"
DB="${DB_PATH:-./projects.db}"
rm -f "$DB"

sqlite3 "$DB" < schema.sql
sqlite3 "$DB" < seed.sql

echo "-- after seed --"
sqlite3 "$DB" "SELECT p.name, p.status, t.name, t.status FROM projects p JOIN tasks t ON t.project_id=p.id;"

sqlite3 "$DB" "UPDATE tasks SET status='done' WHERE name='site-walk';"

OPEN=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks WHERE project_id=1 AND status='open';")
echo "open tasks after site-walk done: $OPEN"
[ "$OPEN" = "3" ] || { echo "FAIL: expected 3 open tasks"; exit 1; }

PROJ=$(sqlite3 "$DB" "SELECT status FROM projects WHERE id=1;")
echo "project status (should still be open): $PROJ"
[ "$PROJ" = "open" ] || { echo "FAIL: project closed too early"; exit 1; }

sqlite3 "$DB" "UPDATE projects SET status='done' WHERE id=1 AND NOT EXISTS (SELECT 1 FROM tasks WHERE project_id=1 AND status='open');"
PROJ=$(sqlite3 "$DB" "SELECT status FROM projects WHERE id=1;")
[ "$PROJ" = "open" ] || { echo "FAIL: close predicate fired with open tasks"; exit 1; }

sqlite3 "$DB" "UPDATE tasks SET status='done';"
sqlite3 "$DB" "UPDATE projects SET status='done' WHERE id=1 AND NOT EXISTS (SELECT 1 FROM tasks WHERE project_id=1 AND status='open');"
PROJ=$(sqlite3 "$DB" "SELECT status FROM projects WHERE id=1;")
echo "project status after all tasks done: $PROJ"
[ "$PROJ" = "done" ] || { echo "FAIL: project did not close"; exit 1; }

echo "CLOSE PREDICATE OK"

python3 -c "
import sqlite3
cx = sqlite3.connect('$DB')
rows = cx.execute('SELECT name,status FROM tasks ORDER BY id').fetchall()
assert len(rows)==4
print('PYTHON READ OK', rows)
"

echo "PERSIST FILE: $DB"
ls -l "$DB"
echo "PERSIST OK — force-quit iSH and reopen this db to finish the test"
