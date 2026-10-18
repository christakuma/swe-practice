package main

import (
	"strconv"
	"sync"
)

// Store keeps every link in memory. A restart forgets them, which is fine for now.
type Store struct {
	mu    sync.Mutex
	links map[string]string
	next  int
}

func NewStore() *Store {
	return &Store{links: map[string]string{}}
}

func (s *Store) Add(url string) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.next++
	code := strconv.FormatInt(int64(s.next), 36)
	s.links[code] = url
	return code
}

func (s *Store) Get(code string) (string, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	url, ok := s.links[code]
	return url, ok
}
