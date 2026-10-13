# Bytes move; bits stay

Revealed after grading. The endianness swap — what `htonl` does on a
little-endian machine.

Reversing bits needed a loop over thirty-two positions. Reversing bytes needs
four fixed moves and no loop at all:

```python
((n & 0x000000FF) << 24) | ((n & 0x0000FF00) << 8)
| ((n & 0x00FF0000) >> 8) | ((n & 0xFF000000) >> 24)
```

The easy mistake is to reach for the bit-reversal you already wrote. It is a
different operation: `0x00000001` bit-reversed is `0x80000000`, and
byte-reversed it is `0x01000000`. The bits inside a byte keep their order.

"Reverse" always needs a unit. Bits, bytes, words, characters, lines — the
same verb, and each one a different function. Asking "reverse the what?"
before starting is the cheapest question in an interview.
