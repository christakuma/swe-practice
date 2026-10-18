# Started is not ready

## What `depends_on` waits for

```yaml
depends_on:
  - db
```

This is compose's short form, and it means `condition: service_started`.
Compose creates and starts the `db` container before the `api` container,
and that is all. It knows nothing about Postgres inside the container. On a
cold start Postgres runs `initdb`, creates the user and database, and runs init
scripts before it accepts a single TCP connection, which takes a few seconds.
The API is a Python script that connects in milliseconds. It loses the race
every time, and on a warm restart (data directory already initialised) it
usually wins, which is the ticket's "run `up` again and it's fine".

## Saying what ready means

Compose can wait for **healthy** instead:

```yaml
api:
  depends_on:
    db:
      condition: service_healthy
db:
  healthcheck:
    test: ["CMD", "pg_isready", "-h", "127.0.0.1", "-U", "orders", "-d", "orders"]
    interval: 2s
    timeout: 3s
    retries: 15
```

`service_healthy` needs `db` to have a healthcheck, and the `postgres` image
does not ship one. Without it, `docker compose up` refuses to start the
project ("dependency failed to start: container ... has no healthcheck
configured"), which you can see for yourself by trying it.

## Why `-h 127.0.0.1`

During first-boot initialisation, the `postgres` image's entrypoint starts a
*temporary* server with `listen_addresses=''`, listening on the Unix socket
and nothing else. (It is line 297 of `docker-entrypoint.sh` in
`postgres:16-alpine`; the exercise checked.) Bare `pg_isready` uses the
socket, so it can say "accepting connections" while TCP, which is how the
API connects, still refuses. With `-h 127.0.0.1` the healthcheck asks the same
way the API will, and only gets a yes from the real server.

## The other fixes, and what they cost

- **`restart: on-failure`** does eventually work: the API crash-loops until
  Postgres happens to be up. It turns a startup ordering problem into a log
  full of `FATAL`, and in a real deployment it trips crash-loop alerts.
- **`sleep 10` before starting** is a guess about how long Postgres takes.
  On a slow laptop or CI runner the guess is wrong, and on a fast one it is
  ten seconds wasted on every start.
- **A healthcheck nobody waits for** shows `healthy` in `docker compose ps`
  and changes nothing about startup order.

## In production

Compose's `depends_on` only orders containers on one host. Kubernetes has no
equivalent at all: pods start independently, and the platform expects every
service to tolerate dependencies that are not there yet, with retries and
readiness probes. The robust fix is both. Declare readiness so the platform can
order things where it is able to, and write services that retry with backoff
for when it is not. This exercise keeps the API's fail-fast rule so that the
compose half has to be right on its own.
