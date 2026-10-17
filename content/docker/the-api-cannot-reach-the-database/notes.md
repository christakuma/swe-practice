# In compose, services find each other by name

## What changed between the laptop and compose

On the laptop, the API and Postgres are two processes on one machine. They
share one network stack, so `localhost:5432` from the API reaches Postgres.

Under compose they are two **containers**, and each container has its own
network namespace, with its own interfaces and its own loopback. `localhost`
inside the `api` container is the `api` container. Postgres is listening on
5432 in a different namespace, and the API's own loopback has nothing on 5432,
so the kernel refuses the connection at once. That is the "refused" in every
log line.

This is the same fact as `connection-reset-from-the-host`, seen from the other
side. There, traffic from outside could not reach a server listening on the
container's loopback. Here, a client using its own loopback cannot reach a
server in a different container.

## What compose gives you instead

`docker compose up` creates a network for the project (`<project>_default`)
and attaches every service to it. Docker's embedded DNS server answers for
each **service name** on that network, so `db` resolves to the database
container's address, and keeps resolving to it if the container is
recreated with a new IP. Hence:

```yaml
DATABASE_URL: postgres://orders:orders@db:5432/orders
```

Note the port. Inside the network, the API talks to the database's
**container** port, 5432, whether or not `db` publishes anything. `ports:` is
only about reaching a container *from the host*.

## The tempting wrong answers

- **`127.0.0.1`** is `localhost` by another name.
- **`network_mode: host`** puts the API in the host's network namespace,
  so its `localhost` becomes the host's. Postgres is not published to the host,
  so it still is not there. On Docker Desktop the "host" is a Linux VM anyway,
  and `ports:` stops working for that service.
- **`host.docker.internal` plus publishing 5432** works on Docker Desktop:
  out through the host and back in. It exposes the database to your whole
  machine and relies on a name Linux hosts do not provide by default. The
  honesty tier confirms both that it connects and why that is not the point.

## Debugging this class of problem

From inside the client container, ask the same question the app asks:

```
docker compose exec api python -c "import socket; print(socket.gethostbyname('db'))"
docker compose exec api python -c "import socket; socket.create_connection(('db', 5432), 2)"
```

`docker network inspect <project>_default` lists which containers are
attached. A service that is missing from that list cannot be reached by name.
