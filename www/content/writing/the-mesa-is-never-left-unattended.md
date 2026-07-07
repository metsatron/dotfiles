---
title: "The Mesa Is Never Left Unattended"
description: "Ceremony-grade computing — what a medicine tradition knows about autonomous agents that the industry hasn't learned yet."
date: 2026-07-04
draft: true
weight: 40
---

In the Shipibo tradition I practice in, the mesa — the working altar, the arranged ground where power is handled — is never left unattended while it is open. This is not superstition about furniture. It is operational security refined over more generations than the software industry has existed: an open channel that nobody is witnessing does not stay aligned to the one who opened it. Things wander in. The work drifts. The practitioner returns to find the space serving intentions that are not his.

I run AI agents all day. The industry's current dream — fully autonomous agents with standing permissions, running unattended, reading email, executing tasks while you sleep — is a mesa left open with the door unlocked, and I want to explain the alternative discipline before the incident reports explain it for me.

## The threat model is ancient

Strip the vocabulary and look at the structure. An autonomous agent with tool access is an open channel with agency, operating in your name, on your resources, exposed to inputs you don't control. The now-classic attacks — prompt injection through a poisoned email, instructions hidden in a webpage the agent reads, a malicious document that redirects the errand — are not exotic. They are possession narratives with a REST API: something spoke to your servant in a voice it mistook for yours.

Every tradition that worked with delegated power converged on the same countermeasures, because the failure mode is structural, not technological. The channel is opened deliberately, with intent stated up front. The work proceeds under witness. The practitioner tests what comes through against what was asked. And the channel is *closed* — sessions end; nothing stays open out of convenience.

Translated: intent-scoped invocation, human witness, verification against the brief, bounded sessions. The industry calls this "human in the loop" and treats it as a temporary embarrassment to be engineered away. The traditions call it the entire discipline, and they are right.

## Conscious CLI

Here is my actual practice, which I'll call ceremony-grade computing without apologizing for the phrase.

I issue commands with intent and I witness the response. When the work is large, I delegate — but delegation means a written brief with the law inlined, verification gates the agent must pass, and a report I actually read. The agent works; I remain the one *working*. On a good day this looks indistinguishable from the autonomous-agent dream, because a well-briefed agent under witness can run for hours. The difference appears at the failure: my failures surface in a report I read that afternoon, inside a blast radius the brief defined. Unattended failures compound silently until they are incidents.

And the discipline has a place for genuine automation — the traditions had one too. Repetitive, deterministic, bounded work belongs in cron: backups, syncs, pipelines, checks. The dividing line is judgment. Anything requiring judgment in my name gets a witness, because judgment is exactly what injection attacks target, and exactly what an unattended channel drifts on. A cron job cannot be talked into anything. An agent can, which is the entire point of an agent, which is why it is never left alone with the door open.

## The economics of the unattended mesa

Notice who profits from the autonomous dream. Unattended agents burn tokens without the natural brake of a human getting tired or suspicious — the vendor's meter runs while you sleep, which is the business model stated plainly. The pitch is that your attention is the expensive part, to be engineered out. The traditions' position is that your attention is the *alignment mechanism*, to be engineered *around* — spent where it multiplies, on intent, briefs, and verification, rather than dribbled away supervising keystrokes.

That reframe changes the target metric. The industry optimizes for autonomy: how long can the agent run without you? I optimize for *leverage under witness*: how much correct work per unit of my genuine attention? These curves look similar in demos and diverge violently in production, because autonomy's costs arrive later, in incident response and trust repair — line items the demo never shows.

## What I'm not saying

Not that agents are dangerous toys — I trust mine with serious work daily. Not that supervision means micromanagement — a good brief is precisely what makes hours of unwatched execution safe. And the tradition's vocabulary is not decoration — change control and code review are its descendants, the guild shape surviving in secular dress. I use the older words because they carry more of the mechanism.

I am saying that the oldest professions of handling power all converged on the same shape — invocation, witness, verification, closure — and the newest one is currently selling the removal of all four as progress. It isn't progress. It is a mesa standing open in an empty room, and everything ancient in me knows exactly how that story goes.

Keep the channel witnessed. Close what you open. The servant does the work; the practitioner does the *willing* — and the willing is the one job that must never be delegated.
