# Counter-example: ship a binary somebody built on their own machine. Small,
# and it only builds where that file happens to exist.
FROM scratch
COPY shortlink /shortlink

EXPOSE 8080
ENTRYPOINT ["/shortlink"]
