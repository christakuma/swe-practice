# `USER` changes who runs, not who owns

## Why the directory exists and still cannot be used

Every instruction before `USER` runs as root, and everything it creates is
root's. Measured on the ticket's image:

```
$ docker run --rm uploads:2.3 sh -c "id; ls -ld /app /app/data"
uid=1000(app) gid=1000(app) groups=1000(app)
drwxr-xr-x 1 root root 4096 Oct 17 21:25 /app
drwxr-xr-x 2 root root 4096 Oct 17 21:25 /app/data
```

Mode 755 on a directory is *owner may write, everyone may enter and list*.
`app` is not the owner, so it may look inside `/app/data` and create
nothing in it. SQLite opens `ledger.db` with permission to create it, the
kernel refuses, and SQLite reports the refusal as `unable to open database
file`, which sounds like a problem with the file and is a problem with its
directory. Without the `RUN mkdir`, the app's own `mkdir` reaches the same
wall one level up: `PermissionError: [Errno 13] Permission denied:
'/app/data'`.

`USER` takes effect for the `RUN` lines after it and for the container. It
changes the ownership of nothing.

## The fix: give it away while you are still root

```dockerfile
RUN useradd --create-home app \
    && mkdir -p /app/data \
    && chown app:app /app/data
USER app
```

Only root may give a file to someone else, so the `chown` has to come
before `USER app`. After it, the build stops:

```
chown: changing ownership of '/app/data': Operation not permitted
```

`install -d -o app -g app /app/data` does the `mkdir` and the `chown` in one
command.

## Answers that work, and why each does

All measured: each builds, starts, and stores an upload.

* **Make the directory as the user.** `USER app` then `WORKDIR /app/data`
  creates it owned by `app`. `WORKDIR` creates every missing directory as
  the `USER` in force at that line, and leaves one that already exists
  alone. Remember to `WORKDIR /app` again afterwards, or `python app.py`
  runs in the wrong directory.
* **Switch user first.** `USER app` before `WORKDIR /app` makes `/app`
  itself `app`'s, and the app creates `data/` at start-up. The files `COPY`
  writes are still root's (`COPY` ignores `USER`), which is fine: the
  service only reads them.
* **`COPY --chown` into a directory `COPY` creates.** `COPY --chown=app:app
  . /app/` with no `WORKDIR` before it makes `/app` and everything in it
  `app`'s, because `COPY` creates a missing destination owned by the
  `--chown` user.
* **A number instead of a name.** `useradd --uid 10001 app` and `USER
  10001` are the same account. Kubernetes' `runAsNonRoot` can only check a
  numeric `USER`, which is a good reason to write one.
* **Any uid, through group 0.** `chgrp 0 /app/data && chmod g+rwx
  /app/data` with `USER 4242`, a uid the image has never heard of. A uid
  with no `/etc/passwd` entry runs with group 0, so the group bits apply.
  This is how images built for OpenShift, which picks the uid at random,
  are written.

## The answer that looks right and is not

```dockerfile
RUN useradd --create-home app
WORKDIR /app
COPY --chown=app:app . .
USER app
```

Every *file* in `/app` is `app`'s now, and `/app` is not: `WORKDIR` created
it as root, and `COPY --chown` leaves a destination that already exists
alone. The app's `mkdir` needs to write `/app` and gets `Permission
denied`. Measured: `ls -ld /app` shows `root root` and `ls -l /app` shows
`app app` for everything in it.

## `chmod 777`

It works, by letting every account in the container write the ledger. On a
directory the service owns, mode 755 already gives the service everything it
needs. Reach for a mode only when the owner cannot be the service, and then
for a group (`775` and `chgrp`), not for everyone.

## A volume does not change this

`VOLUME /app/data`, or `docker run -v ledger:/app/data`, fills a new named
volume from the image's directory, ownership included: a `chown` in the
Dockerfile carries over, and a root-owned directory makes a root-owned
volume. A *bind* mount is different again, because it shows a host
directory whose owner the Dockerfile cannot set at all.

## What the grader reads

It follows ownership through `WORKDIR`, `COPY --chown`, `COPY --from` and
the `mkdir`, `install -d`, `chown`, `chgrp`, `chmod`, `rm`, `useradd` and
`adduser` commands a `RUN` line runs directly, using the same uid numbers
Debian would allocate. What a script does is invisible to it, and so is a
`chown $(id -u app)`. It says so in its verdict when that is why a check
failed, and either way a plain `chown app:app` reads.
