PRAGMA foreign_keys=ON;

DELETE FROM tasks;
DELETE FROM projects;

INSERT INTO projects (name) VALUES ('Xtra Hands — 1420 Maple job');

INSERT INTO tasks (project_id, name)
SELECT id, 'site-walk' FROM projects WHERE name='Xtra Hands — 1420 Maple job';
INSERT INTO tasks (project_id, name)
SELECT id, 'bid' FROM projects WHERE name='Xtra Hands — 1420 Maple job';
INSERT INTO tasks (project_id, name)
SELECT id, 'haul' FROM projects WHERE name='Xtra Hands — 1420 Maple job';
INSERT INTO tasks (project_id, name)
SELECT id, 'surplus log' FROM projects WHERE name='Xtra Hands — 1420 Maple job';
