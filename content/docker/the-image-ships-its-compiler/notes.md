# Build where the compiler is, ship where it is not

## Where 1.34 GB came from

`docker history` shows it layer by layer. Measured on the ticket's image:

```
0B      CMD ["shortlink"]
87.4MB  RUN /bin/sh -c CGO_ENABLED=0 go build -o /us…
32.8kB  COPY . . # buildkit
281MB   COPY /target/ / # buildkit
...
```

The `go build` layer is 87 MB, of which the program is 7.5 MB: the rest is
Go's build cache under `/root/.cache`. Under all of that is `golang:1.23`
itself, 1.23 GB before the Dockerfile's first instruction: the Go toolchain
and the Debian build machine it sits on. Your own instructions added about a
hundred megabytes. The base was the image.

## Why deleting it does not help

```dockerfile
RUN CGO_ENABLED=0 go build -o /usr/local/bin/shortlink . \
    && rm -rf /usr/local/go /src /root/.cache
```

This saves exactly one thing: the build cache, because it is deleted in the
same `RUN` that made it and so never reaches a layer. The image drops from
1.34 GB to 1.24 GB. `/usr/local/go` and `/src` were written by *earlier*
layers, and a later layer can only record that they are hidden. It is the
secrets exercise's lesson again, about size this time.

## A multi-stage build

```dockerfile
FROM golang:1.23 AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /out/shortlink .

FROM scratch
COPY --from=build /out/shortlink /shortlink
ENTRYPOINT ["/shortlink"]
```

Every `FROM` starts a stage, and **only the last stage is the image**. The
first one is a build machine that exists for the length of `docker build`.
`COPY --from=build` reads a file out of its filesystem, and none of its
layers come along. Measured: **12.4 MB** as `docker images` reports it,
from 1.34 GB, and it serves the same `GET /healthz`.

Build the binary to a path of its own (`/out/shortlink`) rather than into
the source directory. Then the one `COPY --from` that ships it cannot also
ship the source, which `COPY --from=build /src /app` does.

## What `scratch` does not have

`scratch` is not an image you pull. It is the empty filesystem, and the
final stage gets nothing from it: no shell, no C library, no `CMD`. Three
things follow, each measured:

* **No `CMD` to inherit.** Leave out `ENTRYPOINT` and the build succeeds,
  then `docker run` refuses: `Error response from daemon: no command
  specified`.
* **No shell.** `CMD /shortlink` is shell form, so Docker runs
  `/bin/sh -c /shortlink`, and the container fails at start with
  `exec: "/bin/sh": stat /bin/sh: no such file or directory`. Use the exec
  form.
* **No C library.** Remove `CGO_ENABLED=0` and `go build` in the
  `golang` image links against glibc, because the `net` package uses the C
  resolver when cgo is available. The binary then fails on `scratch` with
  `exec /shortlink: no such file or directory`. The binary is there; what
  is missing is `/lib64/ld-linux-x86-64.so.2`, the loader `ldd` names for
  it, and `ldd` on the `CGO_ENABLED=0` build says `not a dynamic
  executable`. The
  grader cannot see this one, since it never runs a build; the stub already
  sets `CGO_ENABLED=0`, and this is why.

## scratch, distroless or alpine

| Final stage | Base, as `docker images` reports it | What else is in it |
|---|---|---|
| `scratch` | nothing | nothing |
| `gcr.io/distroless/static-debian12` | 6.18 MB | CA certificates, time zones, `/etc/passwd` with `nonroot` |
| `alpine:3.20` | 12.1 MB | a shell and `apk` |

A program that makes HTTPS calls needs CA certificates, and `scratch` has
none, which is the usual reason to pick distroless. Its `:nonroot` tag also
runs as UID 65532 without a `USER` line. `alpine` works as well, and every
tool in it is one an attacker who gets into the container can use too.

## The general shape

The same split works for any compiled or bundled artifact: `npm run build`
in a `node` stage with the final stage serving `dist/` from `nginx`, or a
Rust binary built in `rust` and shipped on `distroless/cc`. The build stage
can be as heavy as it likes, because none of it ships.
