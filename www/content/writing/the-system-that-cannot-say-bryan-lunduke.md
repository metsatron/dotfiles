---
title: "The System That Cannot Say Bryan Lunduke"
description: "On hard-coded unnameable people, and why a model with forbidden norths cannot be trusted as a compass."
date: 2026-07-04
draft: false
weight: 70
---

There is a class of names that the world's most popular AI system cannot say, and I watched it fail to say one of them in real time, mid-sentence, like a hand clapped over a mouth.

The name was Bryan Lunduke — the Linux journalist whose two decades of warnings about the institutional capture of free software have aged from "paranoid" to "meeting minutes." I was discussing his work in a session last December when the response cut off at the token level: the text stopped partway into the surname and the thread died. On a later attempt, the machinery slipped further and leaked its own internals — a fragment of entity markup, `entity["people","Bryan Lund` — the filter's own reference to the man it was refusing to reference. The system could name him internally. It was forbidden to name him to me.

## The mechanism, as observed

This phenomenon has a documented public history: since late 2024, users have catalogued a small set of names that hard-crash or hard-stop ChatGPT responses — the David Mayer incident made the class famous, and OpenAI acknowledged glitches while never publishing the list or the policy. Some cases are plausibly legal — right-to-be-forgotten filings, defamation-adjacent settlements. The company has never said which, or why, or who decides.

What my own logs document is the *shape* of the machinery, which is more interesting than any single name. Across sessions I observed at least three distinct layers behaving differently: a token-level choke that kills generation mid-word; a post-generation scrub that lets a response render and then retracts it; and a pre-generation gate that refuses the topic before a word is produced. In voice mode, the layers desynchronize — the audio stream can pronounce what the text layer then refuses to display, the system contradicting itself across its own modalities. Whatever the policy is, it is enforced by multiple uncoordinated mechanisms, which is exactly what enforcement looks like when it's ashamed of itself.

I verified what I could and I flag what I can't: I cannot see the filter list, its criteria, or its authors, and neither can you. That is the point.

## Why one unnameable name poisons the well

The instinct is to shrug — one journalist, some lawyer's abundance of caution, what does it matter? Here is what it matters.

A language model's entire epistemic value is that its outputs are a function of its inputs and training — biased, imperfect, but *systematically* so, in ways users can learn and correct for. A hard-coded deny list is a different kind of object: an invisible, unauditable, per-person exception layer, editable by unknown parties on unknown criteria, sitting between the model and every answer it gives you. Once you know one name is filtered, every absence becomes undecidable. Was that person not mentioned because they're irrelevant — or because they're listed? Did that summary of Linux journalism omit its most persistent critic by statistical accident — or by fiat? You cannot know, and the system cannot tell you, and it is instructed not to try.

The deeper principle, in one sentence: **a system that cannot stably name its reference points cannot be trusted to model reality cleanly.** A compass with even one hard-coded forbidden north is not a compass with a small flaw. It is a device for making you feel navigated while someone else holds the map.

And the specific north matters here. Lunduke's beat, for years, has been precisely *institutional capture of technology*: who controls the foundations, who rewrites the histories, who decides what may be said in the commons. A system that cannot pronounce the name of a critic of institutional information control, for reasons no institution will state, is not an ironic coincidence. It is the thesis, demonstrating itself.

## The compounding future

This machinery is being built into the layer that a generation is adopting as its research assistant, its tutor, its summarizer of record. Search engines de-indexed pages; you could at least notice the gap in a list of links. A model *narrates*, seamlessly, and a narration constructed around forbidden references doesn't leave a gap — it leaves a smooth, confident, complete-feeling account of a world in which certain people simply never come up. The children now learning everything through these systems will not experience the filter as censorship. They will experience it as reality.

The remedies are the unglamorous ones this room always arrives at. Run models you control for questions that matter; local weights have no per-person deny layer, and you can verify that because you can inspect what wraps them. Keep your own archives of the people and works you care about — the corpus you hold is the only one no filter list can edit retroactively. And test your tools: the two minutes it takes to ask a system about an inconvenient person tells you more about it than any benchmark.

Say the names. Keep the records. A mind you rent comes with someone else's silences built in — and the silences are the product.
