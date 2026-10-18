# Build where the compiler is, ship where it is not. The final stage starts
# from nothing and takes one file from the builder: the program.
FROM golang:1.23 AS build

WORKDIR /src
COPY . .
# CGO off: a static binary that needs no C library at run time.
RUN CGO_ENABLED=0 go build -o /out/shortlink .

FROM scratch
COPY --from=build /out/shortlink /shortlink

EXPOSE 8080
ENTRYPOINT ["/shortlink"]
