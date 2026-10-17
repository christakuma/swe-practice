# A container's localhost is its own

Two facts produce this ticket, and both are true whatever you run in the
container.

**A container has its own network namespace.** It gets its own interfaces:
a loopback (`127.0.0.1`) that only processes in the same container can reach,
and an interface on a Docker network with an address like `172.17.0.2`. Your
machine's `localhost` and the container's are different places.

**`-p 8000:8000` forwards to the container's network interface.** Docker
listens on port 8000 on your machine and forwards each connection to
`172.17.0.2:8000`, or wherever the container lives. It does not, and
cannot, forward to the container's loopback.

gunicorn binds `127.0.0.1:8000` by default, a sensible choice for a process
on a laptop, where it means "only this machine". In a container it means
"only this container", and published traffic arrives on the one interface
nothing is listening on. On Docker Desktop the connection is accepted at the
edge and then has nowhere to go, so `curl` reports `(52) Empty reply from
server`. On Linux it is more often `(56) Connection reset by peer`. They are
the same bug.

The `docker exec` in the ticket is the key piece of evidence. A request from
*inside* the container reaches `127.0.0.1` and works. That rules out the app,
the port number and the image, and leaves only *where it is listening*.

## What is not the fix

**`EXPOSE`.** The stub already has `EXPOSE 8000`, and it changes nothing about
this ticket. `EXPOSE` is metadata: it documents which port the image expects to
serve on, and `docker run -P` (capital P) reads it to pick ports to publish.
It does not open a port, and it has no effect on what address a process
binds.

**A different port.** `--bind 0.0.0.0:5000` listens in the right place on the
wrong port. `-p 8000:8000` forwards to container port 8000, and nothing is
there either.

**The plain form of `CMD`.** `CMD gunicorn --bind 0.0.0.0:8000 app:app` fixes
the ticket and runs gunicorn through `/bin/sh -c`, which becomes PID 1. A shell
running as PID 1 neither handles SIGTERM nor passes it on, so every `docker stop`
now waits ten seconds and then kills gunicorn mid-request.
`docker-stop-takes-ten-seconds` is that bug on its own.

## Other spellings that work

`--bind :8000` and `--bind [::]:8000` both listen on every interface, and the
grader accepts both. So does `GUNICORN_CMD_ARGS="--bind=0.0.0.0:8000"` in an
`ENV` line, which this exercise rules out only so that there is one place to
look. In a real Dockerfile, the command line is where the next person will
look first.

The same bug, in other servers: Flask's development server (`flask run`
binds `127.0.0.1` unless you pass `--host 0.0.0.0`), uvicorn (`--host`),
Node's `server.listen(port, 'localhost')`, Rails (`-b 0.0.0.0`). Whenever a
containerised service "works inside but not outside", look at the bind address
first.
