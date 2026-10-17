# Three requirements, three mechanisms

Each requirement in the prompt is there because of how Docker works. Each one
fails quietly when it is wrong: the image still builds and the container still
starts.

## Repeatable builds: pin the base

`FROM python:latest` names whichever image was most recently tagged `latest`.
Build on Friday, and again after a new Python release, and you get two
different interpreters from one unchanged Dockerfile. `python:3.12-slim`
pins the minor version. It still moves for patch releases and security
updates, which is usually what you want. `python:3.12-slim@sha256:...` pins
the exact bytes and is what a regulated build uses.

`-slim` is the Debian image without compilers, headers and documentation. Use
the full image when a dependency has to compile a C extension and there is no
wheel for it, and then, ideally, only in a build stage.

## Fast rebuilds: order layers by how often they change

Every instruction produces a layer, and Docker reuses a cached layer until
**its inputs change**. Every layer after that one is rebuilt, whether or not
its own inputs changed. For a `COPY`, the inputs are the files it copies.

```dockerfile
COPY . .                                  # changes whenever any file changes
RUN pip install -r requirements.txt       # so this reruns on every edit
```

```dockerfile
COPY requirements.txt .                   # changes when dependencies change
RUN pip install -r requirements.txt       # cached through ordinary code edits
COPY . .                                  # only this layer is rebuilt
```

The rule generalises: **the things that change least go first.** System
packages, then language dependencies, then your code. The `.dockerignore`
matters here too. Without it, `COPY . .` would also depend on `.git/`, so every
commit would invalidate the layer, even one that changed no source.

## Clean shutdown: be PID 1

`docker stop` sends SIGTERM to the container's PID 1, waits ten seconds, then
sends SIGKILL. Which process is PID 1 depends on how `CMD` is written.

- `CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]`, the **exec
  form**, runs gunicorn directly as PID 1. It receives SIGTERM, finishes
  in-flight requests, and exits.
- `CMD gunicorn --bind 0.0.0.0:8000 app:app`, the **shell form**, runs
  `/bin/sh -c "gunicorn ..."`. The shell is PID 1 and gunicorn is its child.
  The kernel gives PID 1 no default signal handling, so a shell that has not
  installed a SIGTERM handler simply ignores it, and it does not forward it.
  Ten seconds later, everything is killed.

That last point was measured, not assumed. On `python:3.12-slim`, `/bin/sh`
is dash, and dash does *not* replace itself with a lone command the way bash
does. `docker stop` on the shell form takes ten seconds and exits 137 (128 +
SIGKILL's 9).

## Binding 0.0.0.0

Covered in depth in `connection-reset-from-the-host`. The short version:
inside a container, `127.0.0.1` is the container's own loopback, and a
published port never arrives there.

## The advisories

`USER app` means a compromise of the service is not a compromise as root.
`--no-cache-dir` keeps pip's wheel cache, typically tens of megabytes of files
nothing will read again, out of the layer. Neither changes whether the service
works, which is why they are advisories rather than requirements.
