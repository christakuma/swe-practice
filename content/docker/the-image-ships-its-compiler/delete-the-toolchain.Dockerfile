# Counter-example: delete the compiler once it has done its job. The layers
# that brought it are underneath, and ship whatever a later one removes.
FROM golang:1.23

WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /usr/local/bin/shortlink . \
    && rm -rf /usr/local/go /src /root/.cache

EXPOSE 8080
CMD ["shortlink"]
