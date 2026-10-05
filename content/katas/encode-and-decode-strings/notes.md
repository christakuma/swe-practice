# Encode and Decode Strings — count, don't parse

Revealed after grading. The problem is the classic one (LeetCode 271); the
wording above is ours. It is the only kata in the library where you design a
**format** rather than an algorithm, and the lesson transfers directly to every
wire protocol and file format you will ever touch.

## Why a separator cannot work

```python
",".join(strings)
```

Whatever character you pick, a payload is allowed to contain it, and the
decoder has no way to distinguish that occurrence from a real separator. There
is no safe choice — not `\0`, not a rare Unicode code point, not a long magic
string. "Unlikely" is not "impossible", and formats are used for decades.

`test_round_trips_strings_containing_likely_separators` tries nine of the usual
candidates.

## Why escaping is a real fix, and still not enough

```python
",".join(s.replace("\\", "\\\\").replace(",", "\\,") for s in strings)
```

This genuinely solves the collision. The escape character needs escaping too —
and doing it in that order is the whole trick — and then decoding becomes a
character-by-character state machine.

Run it against this suite and it passes fifteen of eighteen tests. The three it
fails are instructive, because none of them is about separators:

```
test_round_trips_an_empty_list
test_distinguishes_no_strings_from_one_empty_string
test_round_trips_every_short_list_of_nasty_strings
```

**`"".split(",")` returns `[""]`, not `[]`.** A join-based format encodes the
empty list and `[""]` to the same text — the empty string — so no decoder can
separate them. The information is simply gone. That is not a bug in the decoder;
it is a format that cannot represent its own domain.

This is the failure worth internalising. Escaping fixes the problem you thought
you had. The empty-list ambiguity is a *second*, independent defect in the same
design, and it is invisible until you test the degenerate cases.

## The move

Put the length in front:

```python
def encode(strings):
    return "".join(f"{len(s)}:{s}" for s in strings)

def decode(encoded):
    strings, i = [], 0
    while i < len(encoded):
        colon = encoded.index(":", i)
        length = int(encoded[i:colon])
        start = colon + 1
        strings.append(encoded[start : start + length])
        i = start + length
    return strings
```

`["hi", ""]` becomes `"2:hi0:"`. Linear both ways.

## The `:` is not a separator

This distinction is the kata, and it is worth being precise about.

A separator sits **between payloads**, so the decoder has to search the payload
for it — which is exactly what arbitrary payloads make impossible.

This `:` terminates **the length**. A length is digits only, so the terminator
cannot occur inside the thing it terminates. The payload is never searched at
all — it is *counted past*. So a payload may contain colons, digits, newlines,
nulls, or a complete valid encoding of a different list, and the decoder cannot
be confused by any of it, because it never looks.

`test_round_trips_a_payload_that_is_itself_an_encoding` is the strongest form of
the attack: the payload is not merely separator-shaped, it is a well-formed
message. A decoder that *parses* unpacks the inner list; a decoder that
*counts* does not care.

That is the general principle, and it is why length-prefixing is what real
protocols use:

> **Make the framing unparseable from the payload, rather than making the
> payload safe for the framing.**

HTTP's `Content-Length`, Redis's RESP, Protocol Buffers' varint-prefixed
fields, netstrings — all the same shape. Escaping is what you do when you are
stuck with a text format somebody else chose.

## The degenerate cases need no special handling

`""` has no digits to read, so the loop never runs and `[]` comes back. `"0:"`
yields one empty slice, so `[""]` comes back. They are different strings, so
they are distinguishable, and neither needs a branch.

Compare with the separator format, where both are `""` and *both* would need a
special case that cannot be written. **A format that represents its edge cases
naturally is a better format than one that needs rules about them** — the same
preference as encoding the default answer in an accumulator's initial value,
from [best time to buy and sell](../best-time-to-buy-and-sell/notes.md).

## On testing a format you did not specify

The format is the solver's choice, so the suite asserts the **property** the
prompt requires — `decode(encode(x)) == x` — rather than an expected encoding.
That is the only honest thing to check, and it is also the stronger one: it
admits every correct format and rejects every incorrect one.

The single exception is `test_distinguishes_no_strings_from_one_empty_string`,
which constrains the encoding directly (`encode([]) != encode([""])`). It has to:
if those two produce the same text, no decoder can be written, so the failure
belongs to `encode` and a round-trip test would blame `decode`.

**Round-trip properties are the cheapest high-value tests available** for
anything with an inverse — serialise/deserialise, compress/decompress,
encrypt/decrypt, parse/print. One line, no expected values to compute wrongly,
and they cover inputs you would never think to enumerate.

## What to take away

**Framing must not be recoverable from the payload.** If your decoder has to
inspect the data to find the boundaries, an adversary — or an ordinary user with
an unusual filename — controls your parser. Count instead.
