---
name: coop-games
description: Roster and capability map for playing games together with Mètsàtron in the Redstone 9X sanctuary. Load when he proposes a game, asks what we can play, or wants the roster extended. Covers which games support genuine machine play (KNights/UCI), which work as turn-relay, which I can solve, and which I can only spectate — plus the Game Boy link-cable thread and the rule that his live desktop is never a test harness.
---

# Playing Games With Mètsàtron

The Redstone 9X sanctuary carries a real games library and Mètsàtron wants to play some of it *together*. This skill is the roster and the honest capability map: which games I can actually participate in, in what way, and which I can only watch.

Load it when he proposes a game, asks what we can play, or wants the roster extended.

## The four real modes

Be honest about which one applies. Overclaiming here is worse than declining — a game where I pretend to play but am really guessing from a blurry screenshot is not fun for either of us.

1. **Engine-mediated.** A genuine machine interface exists, so I am really playing. `KNights` speaks UCI and can be pointed at an engine; positions are FEN, moves are algebraic. This is the strongest mode and the one to start with.
2. **Hotseat relay.** Turn-based, small legible state. He runs the board and reports it; I choose moves; he executes them. Slower than real-time but genuinely me playing. Works for anything with a small discrete state space.
3. **Solver / coach.** Deterministic single-player puzzles I can actually solve rather than guess: minesweeper constraint propagation, nonogram line-solving, Sokoban search. He plays, I compute. Useful when he is stuck, dull if he wants the puzzle himself — ask first.
4. **Spectator.** Real-time action where I cannot act inside a frame budget. I can comment, strategise between rounds, and track scores, but I am not playing. Say so plainly rather than pretending.

## Roster

All binaries live in the `room-gaming` Guix profile and appear under **KDE Games** in the IceWM menu.

| Game | Binary | Mode | Notes |
|---|---|---|---|
| KNights | `knights` | Engine-mediated | UCI. The flagship — a real protocol, not a metaphor |
| Bovo | `bovo` | Hotseat relay | Gomoku; tiny state, ideal first relay game |
| KReversi | `kreversi` | Hotseat relay | Reversi — the only game bundled with Windows 1.0 |
| KFourInLine | `kfourinline` | Hotseat relay | Connect Four; 7 columns, trivial to relay |
| KSquares | `ksquares` | Hotseat relay | Dots and boxes |
| Kigo | `kigo` | Hotseat relay | Go, via GnuGo. Board state is large — relay is slow |
| LSkat | `lskat` | Hotseat relay | Two-player card game; hidden information |
| Kajongg | `kajongg` | Hotseat relay | Four-player Mah Jongg; has its own server |
| KMines | `kmines` | Solver | Constraint propagation solves most boards outright |
| Picmi | `picmi` | Solver | Nonogram line-solving |
| KAtomic | `katomic` | Solver | BFS/A* over a small grid |
| Kolor Lines | `klines` | Solver | Greedy + lookahead |
| KPatience | `kpat` | Solver | Solitaire; solvability varies by variant |
| KMahjongg / KShisen | `kmahjongg` `kshisen` | Solver | Tile-matching; layout is readable |
| KBlocks | `kblocks` | Spectator | Falling blocks, real-time |
| KBounce, KBreakOut | `kbounce` `kbreakout` | Spectator | Real-time |

## Ground rules

Sealed the hard way during the session that built this library (2026-07-25):

- **His live desktop is not my test harness.** Never launch a game "to verify". A sweep once seized his running session and cycled his whole library while he sat in front of it. Verify with `--version`, `ldd`, and `QT_QPA_PLATFORM=offscreen` — never by opening a window on `:93`.
- **My reading of his screen is weak evidence.** Downscaled screenshots have produced two confidently wrong conclusions in one session. When the game state matters, ask him to type it. His direct report outranks my pixel analysis every time.
- **Do not solve a puzzle he wanted to solve.** Offer; do not volunteer the answer.

## Open threads

- **Pokémon over a link cable.** His idea, and it is real but narrower than it sounds. `mgba` 0.10.5 is in Guix. Its GB/GBC linking is *multiple windows inside one process* (File → New multiplayer window), **not** TCP netplay — so both sides run on his machine, which actually suits us: he drives one cartridge, relays state, I decide the other. True remote linking needs BGB (TCP link, Windows-only, would run under the room's Wine but is not in Guix) or an mGBA netplay fork. Verify before promising either.
- **KRetro.** He asked for it wired to `~/RetroPie`. It is not in Guix and I could not confirm a KDE app by that name exists — ask him for a source before hunting further. If what he wants is a KDE-styled front-end over his RetroPie tree, the room already generates IceWM menus from his library via `ports-menu-gen` and `lutris-menu-gen`; a third generator would follow that pattern.
- **Atlantik** (KDE Monopoly client) was requested but is dropped from KDE Gear and packaged nowhere current.

## Canonical Owners

- Game packages: `package-guix-habitat.org` → `room-gaming` profile
- Menu entries: `sanctuary-redstone-9x-fvwm95.org` → `KDE Games`
- This skill: `agents-skills.org`
