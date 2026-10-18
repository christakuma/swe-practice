# Counter-example: the shell form needs a shell, and scratch has none.
FROM golang:1.23 AS build

WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /out/shortlink .

FROM scratch
COPY --from=build /out/shortlink /shortlink

EXPOSE 8080
CMD /shortlink
