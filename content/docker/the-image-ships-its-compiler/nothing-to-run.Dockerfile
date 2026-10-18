# Counter-example: a 12 MB image that does not say what to run. `scratch`
# has no CMD of its own to fall back on.
FROM golang:1.23 AS build

WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /out/shortlink .

FROM scratch
COPY --from=build /out/shortlink /shortlink

EXPOSE 8080
