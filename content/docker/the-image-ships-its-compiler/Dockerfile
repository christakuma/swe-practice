FROM golang:1.23

WORKDIR /src
COPY . .
# CGO off: a static binary that needs no C library at run time.
RUN CGO_ENABLED=0 go build -o /usr/local/bin/shortlink .

EXPOSE 8080
CMD ["shortlink"]
