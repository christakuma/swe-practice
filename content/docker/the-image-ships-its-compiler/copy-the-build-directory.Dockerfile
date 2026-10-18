# Counter-example: two stages, and the builder's whole working directory
# copied across, because that is where the binary was.
FROM golang:1.23 AS build

WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o shortlink .

FROM scratch
COPY --from=build /src /app

EXPOSE 8080
ENTRYPOINT ["/app/shortlink"]
