# Task Patterns Template

Use these patterns when working in DotCortex through OpenCode.

## Pattern: Edit a Managed Config

1. Find the owning `.org` source with `grep -rn "tangle.*path/to/config" *.org`
2. Edit the root `.org` file
3. Run `make tangle`
4. If relevant, run `make preview-stow` or `make safe-stow`
5. Report both the source file changed and the generated effect

## Pattern: Add or Update Package Manifests

1. Identify the correct manager file such as `pip.org`, `npm.org`, or `guix.org`
2. Edit the manifest block in the org source
3. Run `make tangle`
4. Apply with Loom when available, otherwise use the matching `make` target or helper script
5. Mention any machine-specific or Guix-specific constraints

## Pattern: Makefile or Loom Changes

1. Edit `loom.org`, never `Makefile`
2. Re-tangle with `make tangle`
3. Verify the affected target or Loom verb
4. Call out that `Makefile` is generated output

## Pattern: Bootstrap or Fresh Machine Support

1. Start from `INSTALL.sh` and repo docs
2. Check first-tangle `.mk` stub requirements
3. Use `make safe-stow` for first stow, not Loom
4. Check Guix availability and init-system constraints
5. Document any required manual follow-up steps
