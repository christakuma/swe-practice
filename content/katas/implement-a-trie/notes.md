# Implement a Trie — the marker is the whole design

Revealed after grading. The problem is the classic one (LeetCode 208); the
wording above is ours. It is the library's first **data-structure design**
exercise rather than an algorithm, and the first of three that build on each
other.

## The shape

One character per **edge**, not per node. A node is a *prefix*, identified by
the path taken to reach it:

```python
class _Node:
    __slots__ = ("children", "is_word")
    def __init__(self):
        self.children: dict[str, _Node] = {}
        self.is_word = False
```

Walking a word is a loop — step to the child for this character, or stop
because it is absent. Every operation is `O(len(word))` and, the property that
justifies the whole structure, **independent of how many words are stored**.

## `is_word` is not bookkeeping

It is the entire difference between a stored word and a prefix of one. Without
it, inserting `"apple"` makes `contains("app")` true, and `contains` and
`starts_with` collapse into the same function.

`test_does_not_treat_a_prefix_as_a_word` is the discriminating test, and the
structure of the solution makes the reason obvious: `contains` and
`starts_with` are **the same walk**, differing only in what they ask of the
node at the end.

```python
def _find(self, text):        # the shared walk
    ...

def contains(self, word):
    node = self._find(word)
    return node is not None and node.is_word

def starts_with(self, prefix):
    node = self._find(prefix)
    return node is not None and bool(node.is_word or node.children)
```

Keeping the walk in one place is what stops the two queries drifting apart.

## The root is the one node that exists for free

`starts_with` almost needs no subtree search: any node **other than the root**
exists only because an insertion created it, so it necessarily has a word below
it or is one itself.

The root is the exception. On an empty trie, `starts_with("")` reaches the root
and would answer `True` about a collection containing nothing. Since the
question is "does any *stored word* begin with this", the honest answer is
`False` — hence the extra `node.is_word or node.children`.

Worth the clause rather than a shrug. It is a one-line consequence of a real
asymmetry in the structure, and `test_handles_an_empty_trie` pins it. The same
question has a different answer when `""` has actually been inserted, which
`test_handles_the_empty_string_as_a_word` separates.

## When not to build one

A `set` of strings answers `contains` in `O(1)` with three characters of code.
It beats the trie on that operation and on memory, and it is the right choice
whenever exact membership is all you need.

It cannot answer `starts_with` at all without scanning every stored word —
`O(total characters)`. **The trie's entire value is the prefix query**, and
`test_scales_with_word_length_not_vocabulary_size` is the test that separates
them: a hundred thousand stored words, a thousand queries, and the scanning
version does not finish.

Reaching for a trie when a set would do is as much a mistake as the reverse.
The question to ask is whether any query is about *prefixes*.

## `dict` children, not 26 slots

The prompt does not constrain the alphabet, and
`test_handles_non_letter_characters` stores `"é"` and `"日本"`. Third time this
judgement has come up — the same as in
[is it an anagram](../is-it-an-anagram/notes.md) and
[longest run after k replacements](../longest-run-after-k-replacements/notes.md).
The array is faster and correct only when the alphabet is **written down**.

`__slots__` is worth it here in a way it rarely is: a trie allocates one node
per character inserted, so the per-instance `__dict__` a normal class carries
would dominate the memory.

## What to take away

**A data structure is a set of queries plus the state that makes them cheap.**
The trie's node layout follows from wanting prefix queries; `is_word` follows
from wanting to distinguish words from prefixes. Designing one means listing
the questions first and then asking what each node must remember — which is
exactly what the next two katas,
[add and search a word](../add-and-search-a-word/notes.md) and
[find words in a grid](../find-words-in-a-grid/notes.md), extend.
