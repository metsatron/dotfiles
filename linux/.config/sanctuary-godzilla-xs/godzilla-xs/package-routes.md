# Godzilla XS-86000 Package Routes

Active channel audit: Guix `d48f47b30cdf54115fcf018bd3f36c8cabc23636`,
nonguix `d35a2f8f22023426ccf3598fa7079b09bb821e3e`.

Primary emulators absent from active Guix and nonguix:

| System | Primary | Status | Declared next route |
|---|---|---|---|
| X68 BUS | XEiJ (`xeij`) | blocked; PX68k libretro test route available | local XEiJ Guix package or tracked native upstream build using OpenJDK; current launch route is `retroarch -L px68k_libretro.so`; media roots `~/RetroPie/bios/x68000/keropi/`, `~/RetroPie/roms/x68000/` |
| DRIVE A: PC-98 | NP2Kai (`np2kai`) | available in the dedicated Godzilla profile, with room-retropie fallback | local Guix package already built from the pinned NP2kai source; media roots `~/RetroPie/bios/pc98/`, `~/RetroPie/roms/pc98/` |
| DRIVE B: PC-88 | QUASI88 (`quasi88`) | blocked | local Guix package or tracked native upstream build; media roots `~/RetroPie/bios/pc88/`, `~/RetroPie/roms/pc88/` |
| FM TOWNS | Tsugaru (`Tsugaru_CUI`) | available in the dedicated Godzilla profile, with room-retropie fallback | local Guix package already built from the pinned TOWNSEMU source; media roots `~/RetroPie/bios/fmtowns/`, `~/RetroPie/roms/fmtowns/`, `~/RetroPie/roms/scummvm/` |

These are not replaced by RetroArch, DOSBox Staging, MAME, or ScummVM.  Fallback
Wine routes are title-specific only and require user-owned installers under
`~/RetroPie/installers/`.

Package-name notes from this channel:

- `7zip` is available; requested `p7zip` is absent.
- `xdelta` is available; requested `xdelta3` is absent.
- `lhasa` is available; requested `lha` is absent.
- `lutris` is absent from Guix by package name in this channel. It must not be
  exposed to sanctuary-godzilla-xs through a host Flatpak wrapper. The next valid route
  is a sanctuary-native package/build path.
- `flips` is absent from Guix by package name in this channel. It must not be
  exposed to sanctuary-godzilla-xs through a host Flatpak wrapper. The next valid route
  is a sanctuary-native package/build path.
- `mt32emu-qt`, `nuked-sc55`, `bsdiff`, `ucon64`, and `unar` remain absent and
  require packaging work before they can be declared installed.
