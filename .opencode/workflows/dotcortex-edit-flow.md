# DotCortex Edit Flow

Use this workflow for normal repository changes.

## 1. Identify Ownership

Find the owning org source before touching a config:

```bash
cd ~/DotCortex
grep -rn "tangle.*path/to/config" *.org
```

## 2. Edit the Canonical Source

- Change the root `.org` file
- Do not edit `all/`, `linux/`, `debian/`, `devuan/`, `x230/`, `t480s/`, `arch/`, `osx/`, `be/`, or `navi/` directly
- Do not edit `Makefile`; change `loom.org` instead

## 3. Regenerate Output

```bash
cd ~/DotCortex
make tangle
```

## 4. Validate Stow Impact

```bash
cd ~/DotCortex
make preview-stow
```

If the user wants the change applied locally:

```bash
cd ~/DotCortex
make safe-stow
```

## 5. Machine-Specific Apply Options

When Loom is available:

```bash
loom stow:x230
loom stow:t480s
loom stow:devuan
```

Use the right overlay stack for the machine being changed.

## 6. Report Clearly

- Name the `.org` source file edited
- Mention whether `make tangle` and stow-related commands were run
- Mention any gotchas such as Guix path issues or first-stow limitations
