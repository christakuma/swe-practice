# A parser that can be interrupted anywhere

Revealed after grading.

The standard problem's decoder owns the whole string and walks it with an
index. Every local variable — where it is, how long the current string is —
lives for one call. Streaming breaks that: the call ends mid-thought, and
whatever it had worked out has to still be there next time.

So the local variables move into the object:

- **the text that has arrived and not been used yet**, and
- **the length of the string in progress**, once it has been read.

`feed` appends the chunk and then does what the standard decoder did — read a
length, take that many characters — in a loop that stops, without complaint,
whenever it runs out of text.

## Why length prefixes survive and delimiters do not

The format did not have to change, and that is not luck. A length prefix
tells the decoder how much to take *before* it arrives, so "is this string
finished?" is arithmetic. Escaped delimiters can be streamed too, but then a
chunk can end between a backslash and the character it escapes, which is one
more piece of state to carry.

A count of strings at the front (`3\n...`) also works. A terminator at the
*end* does not, in this version: a string must be handed over the moment it
is complete, not when the next thing arrives.

## Where it breaks

- **Parsing each chunk on its own.** Passes when the text arrives whole.
- **A cut inside the length.** `"12` then `3:..."`: the decoder must not
  parse `12` as a length just because the chunk ended.
- **Empty strings.** `0:` is complete with nothing after it, so the loop has
  to emit before it asks for more text.
- **Re-parsing from the start every call**, which also returns every earlier
  string again.

## What the twist was testing

Recognising a state machine. "Reading a length" and "reading a body" are two
states, and the standard solution has them too — implicitly, as two halves of
a loop body. Making input arrive in pieces is the usual thing that forces
implicit state into the open.
