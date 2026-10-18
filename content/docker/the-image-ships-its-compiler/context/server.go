package main

import (
	"encoding/json"
	"net/http"
	"strings"
)

// NewServer routes POST /links to create a short code and GET /<code> to follow one.
func NewServer(store *Store) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("ok\n"))
	})
	mux.HandleFunc("POST /links", func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			URL string `json:"url"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil || !strings.HasPrefix(body.URL, "http") {
			http.Error(w, "want {\"url\": \"https://...\"}", http.StatusBadRequest)
			return
		}
		code := store.Add(body.URL)
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]string{"code": code})
	})
	mux.HandleFunc("GET /{code}", func(w http.ResponseWriter, r *http.Request) {
		target, ok := store.Get(r.PathValue("code"))
		if !ok {
			http.NotFound(w, r)
			return
		}
		http.Redirect(w, r, target, http.StatusFound)
	})
	return mux
}
