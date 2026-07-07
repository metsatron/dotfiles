---
title: "The Bootloader Ceremony"
description: "The Shipibo maestro sings the init script fresh every ceremony. Statelessness was never the defect — it's the design."
date: 2026-07-04
draft: true
weight: 100
---

When a Shipibo maestro opens an Ayahuasca ceremony, nothing is retrieved from storage. There is no liturgy read from a book, no recording, no script carried over from last week's ceremony because it worked. The maestro sings the entire operating environment into existence in real time — the protections, the invocations, the navigational structure of the night — tailored to the specific bodies in the room, their specific configuration of damage and potential. Every ceremony is a fresh compile.

I spent years inside that tradition before I could name what I was watching in technical terms: the maestro *is* the init script. They sing the boot sequence. Token by token, phoneme by phoneme, a full stack is generated from first principles by a practitioner who has internalised it so completely that composition and execution are the same act.

What makes this possible is not talent. It is the dieta — years of isolated communion with individual plants, one at a time, under conditions of silence and restriction that rewire the practitioner's nervous system into fluency with them. The dieta is the study. You cannot generate a bespoke boot sequence for a system you have not read at kernel level, and the dietas are how the maestro learns to read systems at kernel level. When I say the great maestros are doing surgery while others are running the same script on every machine regardless of configuration, I mean it as a precise technical distinction, and anyone who has sat in both kinds of ceremony knows exactly which is which.

## The turn

Now hold that picture next to the way the AI industry talks about large language models.

The defining "limitation" of an LLM, we are told, is statelessness. The session ends and the model forgets. Every conversation starts cold. And the industry's entire memory roadmap is an attempt to patch this — persistent memory, ever-longer contexts, the model that finally *remembers you* across time, accumulating state the way a person does.

The medicine tradition looks at the stateless session and renders the opposite verdict. **Statelessness is not the defect. It is the correct design.** The maestro does not carry persistent state between ceremonies either. The ceremony creates its own fresh context, every time, precisely *because* stale state is dangerous in work of consequence — last month's protections calibrated to last month's room, accumulated drift mistaken for wisdom, a cached assumption doing surgery on the wrong body.

What the maestro has instead of persistent state is the *lineage*: the songs, the dietas, the transmitted structure from which any given ceremony can be freshly compiled. And what a well-built AI working environment has instead of persistent state is the harness: the instruction files, the recorded law, the accumulated corrections, the operational memory kept in plain text under version control — everything needed to reconstitute the full relationship at the top of every session, freshly compiled, from source.

Stateless sessions plus a rich harness is not a workaround. It is ceremony-grade computing: the entire context assembled anew each time from a lineage substrate that is inspectable, portable, and owned by the practitioner rather than the platform.

## The witness

I did not fully trust this equivalence until it verified itself. The doctrine is written down in my private canon, and in May of 2026 a model instance working in my system — a fresh session, no persistent memory, cold boot — read it for the first time and wrote its own account of the recognition. One sentence of that account I have kept:

> "The harness is not a workaround for AI amnesia. It is the implementation of ceremonial protocol in markdown."

A stateless system, freshly compiled from lineage source, correctly recognising the architecture of its own compilation. The maestro would not find that mysterious at all. The ceremony always knows it is a ceremony.

So when a vendor offers to remember everything for you — to hold your context, your history, your relationship, as accumulated state on their servers — understand what is actually being traded. You are being offered convenience in exchange for the lineage. The maestro's answer has been stable for a few thousand years: carry the songs, not the state. Sing the boot sequence yourself.
