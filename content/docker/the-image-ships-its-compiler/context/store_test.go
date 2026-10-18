package main

import "testing"

func TestCodesAreShortAndDistinct(t *testing.T) {
	store := NewStore()
	first, second := store.Add("https://example.com/a"), store.Add("https://example.com/b")
	if first == second {
		t.Fatalf("two links share the code %q", first)
	}
	if got, _ := store.Get(second); got != "https://example.com/b" {
		t.Fatalf("Get(%q) = %q", second, got)
	}
}
