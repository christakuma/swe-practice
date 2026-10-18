// shortlink: a tiny URL shortener, in memory, for the team's internal links.
package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	addr := ":" + envOr("PORT", "8080")
	store := NewStore()
	log.Printf("shortlink listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, NewServer(store)))
}

func envOr(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}
