"""Speaking the reference implementation's protocol, so we can play anyone.

Our own protocol (``core/protocol/``) is six synchronous tools that return
meaningful payloads. The example repository from Appendix D — which most teams
built on — is four *fire-and-forget mailboxes* that always return ``{"ok": true}``
and deliver every answer as a separate inbound call. The two are not variants of
one design; they disagree about what a peer knows and when.

Nothing here replaces `core/protocol`. This is a second, additive path chosen
with ``--protocol reference``, because the audited native path is what our own
tests, self-play and documentation describe, and an opponent's wire format is a
poor reason to disturb it.

See `docs/CONTRADICTIONS.md` C-019 for why this exists at all.
"""
