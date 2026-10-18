# A mount replaces, it does not merge

## What the container sees

The image has this, because `npm ci` ran during the build:

```
/app/package.json
/app/server.js
/app/node_modules/polka/...
```

`- .:/app` mounts the host's project directory at `/app`. A mount does not
combine with what the image has at that path: for as long as the container
runs, `/app` *is* the host directory, and the image's `/app` is underneath
it, unreachable. The host never ran `npm ci`, so it has no `node_modules`,
and neither does the container. `docker run` without the compose file has
no mount, which is why the image looked fine on its own.

The container still shows `Up` because `node --watch` keeps running after
the script fails, waiting for a file to change. On Docker Desktop, where
the ticket's output was captured, the published port accepts the
connection and has nothing listening behind it, so `curl` gets an empty
reply rather than a refusal.

## The fix: a volume inside the bind

```yaml
volumes:
  - .:/app
  - /app/node_modules
```

The second line has no source, so it is an **anonymous volume**. A more
specific mount wins inside a less specific one, so at `/app/node_modules`
the container sees the volume, and everywhere else in `/app` it sees the
host.

What makes it hold the right files is a rule about volumes: **an empty
volume is filled from the image's contents at the mount point the first
time it is mounted.** The modules `npm ci` installed are copied in. A bind
mount has no such rule. It shows whatever the host path holds, and Docker
creates a missing host path empty, which is why
`./node_modules:/app/node_modules` fails exactly as the original did and
leaves an empty `node_modules` directory in your checkout.

The anonymous volume leaves one behind too: an empty directory on the host,
created as a mount point. It is harmless, and worth a line in `.gitignore`.

## Named or anonymous

```yaml
services:
  web:
    volumes:
      - .:/app
      - node_modules:/app/node_modules
volumes:
  node_modules:
```

The same fix with a name. The top-level `volumes:` block is required:
without it compose refuses the file (`service "web" refers to undefined
volume node_modules`).

## The catch: the volume outlives the image

Docker copies the image's files into a volume **only when the volume is
empty**. Compose also keeps a service's anonymous volumes when it recreates
the container. Measured: a file written into `/app/node_modules` survived
`docker compose up -d --build --force-recreate`.

So after you add a dependency and rebuild, the container can still see the
*old* modules. Two ways out:

```
docker compose up -d --build -V      # --renew-anon-volumes
docker compose down -v               # removes the volumes, named ones too
```

Measured: `-V` gave back exactly the image's modules.

## Other ways people solve this

* **Install at startup** (`command: sh -c "npm install && ..."`). It runs, by
  reinstalling from the network on every start, and the result lands in
  your checkout through the bind mount.
* **Mount only the source** (`./src:/app/src`). A good layout when the
  project has a `src/`. This one mounts the whole project on purpose.
* **`docker compose watch`** with `develop.watch` rules, which syncs files
  into the container instead of mounting them, and can rebuild when
  `package.json` changes. It sidesteps the problem entirely, and it is a
  different setup rather than a fix to this one.
