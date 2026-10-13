# Framing was not the whole problem any more

Revealed after grading. A constraint added to "Encode and Decode Strings"
(LeetCode 271) — the one a real wire format has.

The standard solution is a length prefix: write how long each string is, then
the string, untouched. It works because the decoder never has to *look
inside* a payload. That is exactly what stops working here. The payload may
contain a newline or an emoji, and those cannot be sent at all.

So two jobs, not one:

- **Framing** — where does each string start and stop?
- **Representation** — how is a character that cannot travel written with
  ones that can?

```python
"|" + ",".join(f"{ord(character):x}" for character in text)
```

Code points in hex handle representation; the bar in front of each string
handles framing, and distinguishes `[]` from `[""]`.

This is what percent-encoding, base64 and quoted-printable are all for. The
general lesson: when a constraint is put on the *output alphabet*, escaping
or re-encoding is unavoidable, and a length prefix alone will not do.
