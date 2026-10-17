# A deleted file is a hidden file

## Layers, concretely

Every `COPY`, `ADD` and `RUN` that changes the filesystem produces a
**layer**: a tarball of the files that instruction added or changed. An image
is the stack of those tarballs plus a config. A container sees them merged,
top layer winning.

Deleting a file in a later layer cannot reach back into an earlier one.
Instead, the new layer holds a **whiteout**: an empty marker file named
`.wh..env` that tells the merged view to hide `.env`. So after

```dockerfile
COPY . .          # layer A: ... app/.env (with the key in it)
RUN rm -f .env    # layer B: app/.wh..env
```

`ls` in the container shows no `.env`, while layer A still holds the original,
byte for byte. `docker save` hands anyone both layers, and so does a registry.
That is how the scanner found it, and the ticket's output is real: building this
exercise's stub and unpacking the saved image finds `app/.env` with the key.

## The fix: never copy it

Name what the image needs:

```dockerfile
COPY app.py pricing.py ./
```

In a real repository, add a `.dockerignore` as well:

```
.env
.env.*
.git
tests/
```

`.dockerignore` keeps files out of the **build context**, the set of files
Docker can see at all, so even a careless `COPY . .` cannot pick them up. It
is the belt to the explicit copy's braces. This exercise only lets you edit
the Dockerfile so that the lesson is about layers rather than about ignore
files.

## Secrets the build itself needs

Sometimes the build needs a credential, such as a token for a private package
index. Never `ARG` it: build arguments are recorded in `docker history`, and
`ENV` values are written into the image config for `docker inspect` to print.
BuildKit's secret mounts exist for this:

```dockerfile
RUN --mount=type=secret,id=pip_token \
    PIP_INDEX_URL="https://$(cat /run/secrets/pip_token)@pypi.example.com/simple" \
    pip install -r requirements.txt
```

```
docker build --secret id=pip_token,src=token.txt .
```

The secret is mounted for that one `RUN` and written into no layer.

## Multi-stage builds, and the one case where `rm` helps

A *builder* stage can copy everything, delete what it should not pass on, and
hand its result to a clean final stage:

```dockerfile
FROM python:3.12-slim AS build
WORKDIR /app
COPY . .
RUN rm -f .env
FROM python:3.12-slim
COPY --from=build /app /app
```

`COPY --from` copies the builder's *filesystem*, after the delete, rather than
its layers, so the final image never holds `.env`. The grader models this and
accepts it, and the honesty tier confirms it against a real build. The builder's
layers still exist in the build cache on the machine that built it, which is
one more reason the explicit copy is the simpler answer.

## If a secret has already shipped

Rotate it. Rebuilding the image removes the key from *new* images, but every
copy already pulled, cached or mirrored still has it, and it stays valid until
it is revoked.
