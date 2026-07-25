;; Maak control plane (Scheme, XDG-friendly)

;; [[file:../../../loom.org::*Maak control plane (Scheme, XDG-friendly)][Maak control plane (Scheme, XDG-friendly):1]]
(use-modules (srfi srfi-1)
             (srfi srfi-13)        ; string-prefix?, string-contains
             (ice-9 match)
             (ice-9 pretty-print)
             (ice-9 format))

;; Run one shell string via bash -lc <cmd> with inherited TTY/stdout/stderr,
;; so long-running tasks stream live output and color-capable tools keep ANSI.
(define (exit-status status)
  (cond
   ((not status) 127)
   ((status:exit-val status) => identity)
   ((status:term-sig status) => (lambda (sig) (+ 128 sig)))
   (else 1)))

(define (sh cmd)
  (exit-status (system* "bash" "-lc" cmd)))

(define (run-sequential . cmds)
  (let loop ((cmds cmds)
             (first-failure 0))
    (if (null? cmds)
        first-failure
        (let ((code (sh (car cmds))))
          (loop (cdr cmds)
                (if (and (zero? first-failure) (not (zero? code)))
                    code
                    first-failure))))))

(define (ok? code) (zero? code))
(define (task name desc thunk) (list name desc thunk))
(define (task-name t)  (list-ref t 0))
(define (task-desc t)  (list-ref t 1))
(define (task-thunk t) (list-ref t 2))

(define HOME (or (getenv "HOME") (error "HOME not set")))
(define CORE-PROFILE (string-append HOME "/.guix-extra-profiles/core/core"))

(define (clean-guix-env cmd)
  (string-append
   "env -u GUILE_LOAD_PATH -u GUILE_LOAD_COMPILED_PATH -u GUILE_SYSTEM_PATH -u GUIX_PACKAGE_PATH "
   "PATH=\"" HOME "/.config/guix/current/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:$PATH\" "
   cmd))

(define (mk-guix cmd)
  (sh (clean-guix-env
       (string-append "make -f " HOME "/DotCortex/all/.mk/guix.mk " cmd))))

(define (mk-guix-root cmd)
  (sh (string-append "make -f " HOME "/DotCortex/all/.mk/guix-root.mk " cmd)))

;; Generic target runner. The root Makefile includes every all/.mk/*.mk fragment,
;; so this resolves flatpak-*, plasmoid-*, kwin-borderless-* and icons-* alike.
;; It previously hardcoded "-f flatpak.mk", which silently broke all 7 non-flatpak
;; verbs routed through mk (plasmoid:{apply,diff,health,reload}, kwin-borderless:*).
(define (mk cmd)
  (sh (string-append "make -C " HOME "/DotCortex " cmd)))

(define (mk-appimage cmd)
  (let* ((HOME (or (getenv "HOME") ""))
         (mk (string-append "make -f " HOME "/DotCortex/all/.mk/appimage.mk " cmd)))
    (sh mk)))

(define (with-core thunk)
  (let* ((cmd (string-append ". \"" CORE-PROFILE "/etc/profile\"; " (thunk))))
    (sh cmd)))

(define (git-submodules-latest-cmd)
  (string-append
   "git submodule foreach --recursive '"
   "branch=$(git -C \"$toplevel/$name\" remote show origin | sed -n \"s#.*HEAD branch: ##p\"); "
   "if [ -z \"$branch\" ]; then branch=$(git config -f \"$toplevel/.gitmodules\" --get submodule.$name.branch || echo master); fi; "
   "git fetch origin \"$branch\" && git checkout -q FETCH_HEAD'"))

(define (git-submodules-sync-cmd)
  "git submodule sync --recursive && git submodule update --init --recursive")

(define (git-submodules-status-cmd)
  "git submodule status --recursive")

;; After stow, reload tmux config in the running server (if any).
;; Ensures that changed options like @resurrect-save-script-path take effect
;; without requiring a full server restart.
;; Bash login shells spawned by Guile don't inherit Guix PATH, so we prepend it.
(define (stow-then-reload-tmux stow-cmd)
  (let ((result (sh stow-cmd)))
    (sh (string-append
         "PATH=\"" HOME "/.guix-extra-profiles/core/core/bin:$PATH\" "
         "tmux source-file ~/.config/tmux/tmux.conf >/dev/null 2>&1 "
         "&& printf '[loom] tmux config reloaded\\n' "
         "|| printf '[loom] tmux: not running, skipped reload\\n'"))
    result))

;; Safety: ensure task constructor is always bound at top level (idempotent)
(define task
  (lambda (name desc thunk)
    (list name desc thunk)))

(define tasks
  (list
   ;; --- Top level / meta ---
   (task 'list "List available tasks"
         (lambda ()
           (for-each
            (lambda (t)
              (format #t "~a\t~a~%" (task-name t) (task-desc t)))
            tasks)
           0))

   (task 'all "TOC -> tangle -> census -> ensure Guix dirs"
         (lambda () (sh "make all")))

   (task 'lint "Structural + style lint over root org sources"
         (lambda () (mk "lint")))

   (task 'census "Verify org parses every declared src block (silent-drop detector)"
         (lambda () (mk "census")))

   (task 'hooks:install
         "Install tracked DotCortex git hooks for this checkout"
         (lambda ()
           (sh "HELPER=\"$HOME/.local/bin/dotcortex-install-git-hooks\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/all/.local/bin/dotcortex-install-git-hooks\"; \"$HELPER\"")))

   (task 'hooks:health
         "Show the active git hooks path for this checkout"
         (lambda () (sh "git config --get core.hooksPath || echo '(unset)'")))

   (task 'codex:apply
         "Apply DotCortex-managed Codex local config patches"
         (lambda () (sh "HELPER=\"$HOME/.local/bin/codex-config-apply\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/all/.local/bin/codex-config-apply\"; \"$HELPER\"")))

   ;; --- Git maintenance ---
   (task 'git:submodules
         "Update all submodules to the latest commit on their tracked branch"
         (lambda () (sh (git-submodules-latest-cmd))))

   (task 'git:submodules:latest
         "Alias for git:submodules"
         (lambda () (sh (git-submodules-latest-cmd))))

   (task 'git:submodules:sync
         "Sync submodule URLs and initialize/update recursively"
         (lambda () (sh (git-submodules-sync-cmd))))

   (task 'git:submodules:status
         "Show recursive submodule status"
         (lambda () (sh (git-submodules-status-cmd))))

   ;; --- Stow / dotfiles ---
   (task 'stow "Safe stow shared overlay only (all)"
         (lambda () (stow-then-reload-tmux "make safe-stow")))

   (task 'stow:linux "Safe stow shared + linux overlays (all linux)"
         (lambda () (stow-then-reload-tmux "STOW_PKGS='all linux' make safe-stow")))

   (task 'stow:debian "Safe stow shared + linux + debian overlays (all linux debian)"
         (lambda () (stow-then-reload-tmux "STOW_PKGS='all linux debian' make safe-stow")))

   (task 'stow:x230 "Safe stow X230 overlays (all linux debian x230)"
         (lambda () (stow-then-reload-tmux "STOW_PKGS='all linux debian x230' make safe-stow")))

   (task 'stow:t480s "Safe stow T480s overlays (all linux debian devuan t480s)"
         (lambda () (stow-then-reload-tmux "STOW_PKGS='all linux debian devuan t480s' make safe-stow")))

   (task 'stow:devuan "Safe stow shared + linux + devuan overlays (all linux devuan)"
         (lambda () (stow-then-reload-tmux "STOW_PKGS='all linux devuan' make safe-stow")))

   (task 'stow:openmandriva "Safe stow OpenMandriva overlays (all linux openmandriva)"
         (lambda () (stow-then-reload-tmux "STOW_PKGS='all linux openmandriva' make safe-stow")))

   (task 'stow:t480 "Safe stow T480 Vendefoul Wolf overlays (all linux debian t480)"
         (lambda () (stow-then-reload-tmux "STOW_PKGS='all linux debian t480' make safe-stow")))

   (task 'stow:s24 "Safe stow S24 overlays (all termux s24)"
         (lambda () (stow-then-reload-tmux "STOW_PKGS='all termux s24' make safe-stow")))

   (task 'stow:health
         "Scan broken symlinks under $HOME, optionally clean Stow orphans"
         (lambda ()
           (sh "dotcortex-stow-health")))

    (task 'health "Show registrar, GTK module, and nvim path"
          (lambda ()
            (sh "pgrep -af appmenu-registrar || echo 'registrar process: (none)'")
            (sh "gdbus call --session --dest com.canonical.AppMenu.Registrar --object-path /com/canonical/AppMenu/Registrar --method org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1 && echo 'registrar bus: reachable' || echo 'registrar bus: unreachable'")
            (sh "printf 'GTK_MODULES=%s\\n' \"${GTK_MODULES:-}\"")
            (sh "xfconf-query -c xsettings -p /Gtk/ShellShowsMenubar 2>/dev/null || echo 'Gtk/ShellShowsMenubar: (unset)'")
            (sh "xfconf-query -c xsettings -p /Gtk/ShellShowsAppmenu 2>/dev/null || echo 'Gtk/ShellShowsAppmenu: (unset)'")
           (with-core (lambda () "command -v nvim; nvim --version | sed -n '1,2p'"))
           0))

   (task 'desktop:heal "Restart desktop components for the current DE"
         (lambda ()
           (sh "HELPER=\"$HOME/.local/bin/desktop-heal\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/linux/.local/bin/desktop-heal\"; \"$HELPER\"")))

   (task 'redstone:refresh
         "Project current DotCortex config into the running Redstone 9X room and reload it"
         (lambda ()
           (sh "HELPER=\"$HOME/.local/bin/sanctuary-redstone-9x-refresh\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/linux/.local/bin/sanctuary-redstone-9x-refresh\"; \"$HELPER\"")))

   (task 'redstone:check
         "Report stale projected files in the running Redstone 9X room"
         (lambda ()
           (sh "HELPER=\"$HOME/.local/bin/sanctuary-redstone-9x-refresh\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/linux/.local/bin/sanctuary-redstone-9x-refresh\"; \"$HELPER\" --check")))

   (task 'redstone:layout
         "Apply the declared Redstone 9X desktop icon layout and bounce the desktop"
         (lambda ()
           (sh "HELPER=\"$HOME/.local/bin/sanctuary-redstone-9x-refresh\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/linux/.local/bin/sanctuary-redstone-9x-refresh\"; \"$HELPER\" --layout")))

   (task 'redstone:programs
         "Reproject the Redstone 9X Programs menu as a browsable directory tree"
         (lambda ()
           (sh "GH=\"$HOME/.local/share/dotcortex/guests/sanctuary-redstone-9x/home\"; HELPER=\"$GH/.local/bin/redstone-9x-program-tree\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/linux/.local/bin/redstone-9x-program-tree\"; HOME=\"$GH\" /bin/bash \"$HELPER\"")))

   (task 'redstone:layout-capture
         "Freeze the running room's current desktop icon arrangement into the manifest"
         (lambda ()
           (sh "HELPER=\"$HOME/.local/bin/sanctuary-redstone-9x-refresh\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/linux/.local/bin/sanctuary-redstone-9x-refresh\"; \"$HELPER\" --capture-layout")))

   (task 'desktop:appmenu "Configure XFCE appmenu xsettings and registrar"
         (lambda ()
           (sh "HELPER=\"$HOME/.local/bin/xfce-appmenu-configure\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/linux/.local/bin/xfce-appmenu-configure\"; \"$HELPER\"")))

   (task 'defaults:apply
         "Apply declared desktop defaults through platform tools"
         (lambda ()
           (sh "HELPER=\"$HOME/.local/bin/defaults-apply\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/linux/.local/bin/defaults-apply\"; \"$HELPER\"")))

   (task 'defaults:diff
         "Show declared desktop defaults vs live state"
         (lambda ()
           (sh "HELPER=\"$HOME/.local/bin/defaults-diff\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/linux/.local/bin/defaults-diff\"; \"$HELPER\"")))

   (task 'defaults:health
         "Show current MIME and DE preferred-app defaults"
         (lambda ()
           (sh "HELPER=\"$HOME/.local/bin/defaults-health\"; [ -x \"$HELPER\" ] || HELPER=\"$HOME/DotCortex/linux/.local/bin/defaults-health\"; \"$HELPER\"")))

   (task 'swap:heal
         "Safe swap purge + XFCE/Flatpak heal (with RAM safety checks)"
         (lambda ()
           (sh "swap-heal")))

   (task 'swap:heal!
         "Force swap purge (SWAP_HEAL_FORCE=1) - may OOM the system"
         (lambda ()
           (sh "SWAP_HEAL_FORCE=1 swap-heal")))

   ;; --- Guix user profile ---
   (task 'guix:pull "guix pull (update channels)"
         (lambda () (mk-guix "guix-pull")))

   (task 'guix:apply "Build core+dev profiles"
         (lambda () (mk-guix "guix-core guix-dev guix-nonguix")))

   ;; CPU-tuned local inference. Deliberately NOT folded into guix:apply — the transformed
   ;; ggml/llama.cpp/whisper.cpp have no substitutes and compile from source, so applying
   ;; this is a per-machine decision. The build is multi-variant (GGML_CPU_ALL_VARIANTS)
   ;; and therefore portable, unlike an -march=native build. Apply on the local-inference
   ;; fallbacks: T480s, T480, and the T1700 when it lands. Never the X230 — fileserver.
   (task 'guix:inference-apply "Build CPU-tuned inference profile (llama.cpp + whisper.cpp, multi-variant CPU backends)"
         (lambda () (mk-guix "guix-inference")))

   ;; Virtual Habitat sanctuary substrate profiles (Phase 0B declared; apply in Phase 1A)
   (task 'guix:sanctuary-apply "Build desktop-common + sanctuary + gaming + windows-compat + retropie Guix profiles"
         (lambda () (mk-guix "guix-desktop-common guix-sanctuary-qtile guix-sanctuary-gnustep guix-sanctuary-cde guix-sanctuary-godzilla-xs guix-room-gaming guix-room-windows-compat guix-room-retropie")))

   ;; Per-sanctuary / per-room apply verbs. The combined guix:sanctuary-apply is one
   ;; fail-fast make chain, so a single broken profile (e.g. an upstream test failure
   ;; in a CDE app dependency) aborts every later profile. These land one profile at a
   ;; time — each make target already declares its own prereqs (desktop-common or
   ;; guix-dirs), so they are self-sufficient — keeping fail-fast semantics per verb
   ;; (no -k, no muted failures) while letting one wing be applied independently.
   (task 'guix:desktop-common "Build the shared desktop-common Guix profile"
         (lambda () (mk-guix "guix-desktop-common")))
   (task 'guix:qtile-apply "Build sanctuary-qtile profile (+ desktop-common)"
         (lambda () (mk-guix "guix-sanctuary-qtile")))
   (task 'guix:gnustep-apply "Build sanctuary-gnustep profile (+ desktop-common)"
         (lambda () (mk-guix "guix-sanctuary-gnustep")))
   (task 'guix:cde-apply "Build sanctuary-cde profile (+ desktop-common)"
         (lambda () (mk-guix "guix-sanctuary-cde")))
   (task 'guix:sx-apply "Build sanctuary-godzilla-xs profile (+ desktop-common)"
         (lambda () (mk-guix "guix-sanctuary-godzilla-xs")))
   (task 'guix:gaming-apply "Build room-gaming profile (+ desktop-common)"
         (lambda () (mk-guix "guix-room-gaming")))
   (task 'guix:windows-compat-apply "Build room-windows-compat profile (+ desktop-common)"
         (lambda () (mk-guix "guix-room-windows-compat")))
   (task 'guix:fvwm95-apply "Build room-fvwm95 profile"
         (lambda () (mk-guix "guix-room-fvwm95")))
   (task 'guix:ice2k-apply "Build room-ice2k profile (FOX toolchain for the ice2k Windows-component build)"
         (lambda () (mk-guix "guix-room-ice2k")))
   (task 'guix:retropie-apply "Build room-retropie profile (retroarch, mame, ES fork, cores, X68000/PC-98/FM-TOWNS)"
         (lambda () (mk-guix "guix-room-retropie")))

   (task 'guix:git-bench
         "Probe guix channel mirrors and print the fastest URL (writes cache)"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/guix.mk guix-pull-bench")))

   (task 'guix:git-apply
         "Apply fastest guix pull mirror to ~/.config/guix/channels.scm"
         (lambda () (sh "~/DotCortex/all/.local/bin/guix-apply-pull-url")))

   (task 'guix:dirs "Ensure ancillary Guix directories"
         (lambda () (mk-guix "guix-dirs")))

   ;; (task 'guix:core "Build core profile from manifest"
   ;;       (lambda () (mk-guix "guix-core")))
   ;; (task 'guix:dev "Build dev profile (depends on core)"
   ;;       (lambda () (mk-guix "guix-dev")))
   ;; (task 'guix:nonguix "Build Nonguix profile from manifest"
   ;;       (lambda () (mk-guix "guix-nonguix")))

   (task 'guix:gc
         "Collect unreferenced store items (reclaim disk space; safe)"
         (lambda () (mk-guix "guix-gc")))

   ;; --- Guix substitute bench/apply ---
   (task 'guix:sub-bench
         "Benchmark Guix substitute servers and print best order"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/guix-substitutes.mk guix-sub-bench")))

   (task 'guix:sub-apply
         "Apply the best substitute server order to guix-daemon"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/guix-substitutes.mk guix-sub-apply")))

   ;; --- Which binaries (user) ---
   (task 'which-nvim "Show nvim location and version"
         (lambda ()
           (with-core (lambda () "command -v nvim; nvim --version | sed -n '1,2p'"))
           0))

   (task 'which-zsh "Show zsh location and version"
         (lambda ()
           (with-core (lambda () "command -v zsh; zsh --version | sed -n '1,2p'"))
           0))

   ;; --- Root integration / Guix root ---
   (task 'root:sync
         "Sync dotfiles configs into root (channels, manifest, nvim)"
         (lambda () (sh "~/DotCortex/all/.local/bin/root-sync")))

   (task 'guix:pull-root "guix pull for root using synced channels"
         (lambda () (mk-guix-root "guix-root-pull")))

   (task 'guix:root "Apply root manifest to root profile"
         (lambda () (mk-guix-root "guix-root-apply")))

   (task 'guix:gc-root "Collect unreferenced store items for root"
         (lambda () (mk-guix-root "guix-root-gc")))

   (task 'root:config
         "Apply root-level configs that need sudo (Early OOM etc.)"
         (lambda () (sh "MODE=balanced ~/DotCortex/x230/.local/bin/earlyoom-balanced")))

   (task 'root:earlyoom-dryrun
         "Show what earlyoom would kill, without killing"
         (lambda ()
           (sh "sudo systemctl stop earlyoom && sudo earlyoom --dryrun -m 5,3 -s 15,10 \
        --prefer '^(kdeconnectd|fluidsynth|jellyfin|[Oo]bsidian|Telegram|WebExtensions|qmmp)$' \
        --avoid  '^(floorp|thunar|gvfs.*)$'; sudo systemctl start earlyoom")))

   (task 'root:which-nvim "Show root nvim location and version"
         (lambda ()
           (sh "sudo -i sh -lc 'command -v nvim; nvim --version | sed -n \"1,2p\"'")))

   ;; --- Flatpak ---
   (task 'flatpak:apply
         "Enforce exact match (set ENFORCE/UNINSTALL/FO... vars as needed)"
         (lambda () (mk "flatpak-apply")))

   (task 'flatpak:diff "Plan: desired (SSV) vs installed"
         (lambda () (mk "flatpak-diff")))

   (task 'flatpak:bridge "Apply Flatpak desktop + per-app bridges"
         (lambda () (sh "make flatpak-bridge")))

    (task 'flatpak:x11 "Re-stow x230/.xsessionrc & friends"
          (lambda () (sh "make x11-apply")))

    (task 'icons:sync "Copy icon/theme trees into home and rebuild caches"
          (lambda () (sh "make icons-sync")))

    (task 'desktop:icon-cache
          "Rebuild missing icon-theme.cache files system-wide (user + root-owned packs; sudo batched once)"
          (lambda () (sh "make icon-cache-rebuild")))

     (task 'flatpak:remotes
           "Ensure remotes (user+system) with clean env"
           (lambda () (mk "flatpak-remotes")))

    (task 'flatpak:release-diff
          "Check release-backed Flatpak bundles managed via GitHub"
          (lambda () (mk "flatpak-release-diff")))

   ;; (task 'flatpak:capture
   ;;       "Capture live apps -> linux/.flatpak/manifest/apps.ssv"
   ;;       (lambda () (mk "flatpak-capture")))
   ;; (task 'flatpak:sync
   ;;       "Additive apply (no removals)"
   ;;       (lambda () (mk "flatpak-sync")))

   (task 'flatpak:perms-capture "Capture per-app permissions/overrides"
         (lambda () (mk "flatpak-perms-capture")))

   (task 'flatpak:perms-apply "Apply captured permissions/overrides"
         (lambda () (mk "flatpak-perms-apply")))

   ;; --- Snap ---
   (task 'snap:sync
         "Install or refresh everything in the manifest, no removals"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/snap.mk snap-apply")))

   (task 'snap:apply
         "Install from manifest, uninstall extras (safe, keeps protected bases)"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/snap.mk snap-enforce")))

   (task 'snap:apply!
         "Install from manifest, uninstall extras, allow protected removals"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/snap.mk snap-enforce-force")))

   ;; (task 'snap:sync-dry "Dry run of sync"
   ;;       (lambda () (sh "make -f ~/DotCortex/all/.mk/snap.mk snap-apply-dry")))

   (task 'snap:prune "Remove all disabled snap revisions"
         (lambda () (sh "~/DotCortex/all/.local/bin/snap-prune-disabled")))

   ;; (task 'snap:autoremove-list
   ;;       "Dry run: prune disabled, remove unused content snaps and bases"
   ;;       (lambda () (sh "~/DotCortex/all/.local/bin/snap-autoremove")))

   (task 'snap:autoremove
         "Execute: same as above, with removals"
         (lambda () (sh "~/DotCortex/all/.local/bin/snap-autoremove --yes")))

   (task 'snap:orphans "List orphaned user data dirs under ~/snap"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/snap.mk snap-list-orphans")))

   ;; (task 'snap:purge-data!
   ;;       "Execute: also purge orphaned data dirs under ~/snap and /var/snap"
   ;;       (lambda () (sh "~/DotCortex/all/.local/bin/snap-autoremove --yes --purge-data")))

   (task 'snap:connections "Show consumers of common content snaps"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/snap.mk snap-connections")))

   (task 'snap:capture
         "Capture installed apps -> all/.snap/manifest/apps.ssv"
         (lambda () (sh "~/DotCortex/all/.local/bin/snap-capture")))

   (task 'snap:diff "Plan: show manifest vs installed"
         (lambda () (sh "~/DotCortex/all/.local/bin/snap-diff")))

    ;; --- AppImage ---
    (task 'appimage:integrate
          "Install/enable appimaged user service from the newest AppImage"
          (lambda () (sh "~/.local/bin/appimage-integrator-setup")))

    (task 'appimage:update
          "Update all AppImages (Auto-integrate, scrub desktops)"
          (lambda () (sh "make -f ~/DotCortex/all/.mk/appimage.mk appimage-update")))

   ;; Back-compat alias
   (task 'appimage:ail-scrub
         "Deactivate/clean AIL bits (manual, safe to keep for later)"
         (lambda () (sh "~/.local/bin/appimage-ail-scrub")))

   (task 'appimage:health
         "Show appimaged/AIL state and last 50 log lines"
         (lambda () (sh "~/.local/bin/appimage-health")))

(task 'appimage:inventory
  "Classify AppImages: supports/manual/dead and write SSVs"
  (lambda () (sh "~/.local/bin/appimage-inventory")))

(task 'appimage:apply
  "Hybrid update: ZSync pass + conf pass (alias for appimage:update)"
  (lambda () (sh "make -f ~/DotCortex/all/.mk/appimage.mk appimage-update")))

(task 'appimage:release-list
  "List all conf-managed AppImages"
  (lambda () (sh "~/.local/bin/apprelease list")))

(task 'appimage:release-update-all
  "Update all conf-managed AppImages via apprelease"
  (lambda () (sh "~/.local/bin/apprelease update-all")))

(task 'appimage:release-health
  "Check forge reachability for all conf-managed AppImages"
  (lambda () (sh "for a in $(~/.local/bin/apprelease list); do ~/.local/bin/apprelease health \"$a\" 2>&1 || true; done")))

;; --- AM / AppMan (ivan-hc/AM, user mode) ---
(task 'am:bootstrap
  "Install ~/.local/bin/appman and seed appman-config (idempotent)"
  (lambda () (sh "make -f ~/DotCortex/all/.mk/am.mk am-bootstrap")))

(task 'am:apply
  "Install manifest apps via appman, no removals"
  (lambda () (sh "make -f ~/DotCortex/all/.mk/am.mk am-apply")))

(task 'am:apply!
  "Install from manifest AND remove extras not listed"
  (lambda () (sh "make -f ~/DotCortex/all/.mk/am.mk am-enforce")))

(task 'am:diff "Plan: manifest vs installed AppMan apps"
  (lambda () (sh "make -f ~/DotCortex/all/.mk/am.mk am-diff")))

(task 'am:capture
  "Capture installed apps -> all/.am/manifest/apps.ssv"
  (lambda () (sh "make -f ~/DotCortex/all/.mk/am.mk am-capture")))

(task 'am:update "Update all AppMan apps and appman itself (appman -u)"
  (lambda () (sh "make -f ~/DotCortex/all/.mk/am.mk am-update")))

(task 'am:clean "Remove orphaned launchers/symlinks (appman -c)"
  (lambda () (sh "make -f ~/DotCortex/all/.mk/am.mk am-clean")))

(task 'am:health "Show appman binary, config, apps dir, manifest state"
  (lambda () (sh "make -f ~/DotCortex/all/.mk/am.mk am-health")))

;; --- Plasmoid (pinned Plasma 6 panel applets) ---
(task 'plasmoid:apply
      "Install/upgrade pinned Plasma applets from manifest (verifies commit lock)"
      (lambda () (mk "plasmoid-apply")))

(task 'plasmoid:diff "Show manifest vs installed applet state"
      (lambda () (mk "plasmoid-diff")))

(task 'plasmoid:health "Show Plasma 6 tooling, installed applets, kwin toggle state"
      (lambda () (mk "plasmoid-health")))

(task 'plasmoid:reload "Replace plasmashell to pick up applet changes"
      (lambda () (mk "plasmoid-reload")))

(task 'kwin:borderless-status "Show BorderlessMaximizedWindows state"
      (lambda () (mk "kwin-borderless-status")))

(task 'kwin:borderless-on
      "Hide titlebars on maximized windows (backs up kwinrc, live reconfigure)"
      (lambda () (mk "kwin-borderless-on")))

(task 'kwin:borderless-off
      "Restore titlebars on maximized windows"
      (lambda () (mk "kwin-borderless-off")))

;; --- XFCE Desktop Menu (SonicDE shape on XFCE) ---
(task 'desktop:xfce-menu-build
      "Build+install the native xfce-desktop-menubar panel plugin (user-scope)"
      (lambda ()
        (sh "H=\"$HOME/.local/bin/xfce-desktop-menubar-build\"; [ -x \"$H\" ] || H=\"$HOME/DotCortex/linux/.local/bin/xfce-desktop-menubar-build\"; \"$H\"")))

(task 'desktop:xfce-menu-configure
      "Add appmenu + windowck + desktop-menubar plugins to the top panel (additive)"
      (lambda ()
        (sh "H=\"$HOME/.local/bin/xfce-desktopmenu-configure\"; [ -x \"$H\" ] || H=\"$HOME/DotCortex/linux/.local/bin/xfce-desktopmenu-configure\"; \"$H\"")))

(task 'desktop:xfce-menu
      "Build the desktop menubar plugin then place all panel plugins"
      (lambda ()
        (sh "B=\"$HOME/.local/bin/xfce-desktop-menubar-build\"; [ -x \"$B\" ] || B=\"$HOME/DotCortex/linux/.local/bin/xfce-desktop-menubar-build\"; C=\"$HOME/.local/bin/xfce-desktopmenu-configure\"; [ -x \"$C\" ] || C=\"$HOME/DotCortex/linux/.local/bin/xfce-desktopmenu-configure\"; \"$B\" && \"$C\"")))

(task 'xfwm:titleless-status "Show xfwm4 titleless/borderless maximize state"
      (lambda ()
        (sh "H=\"$HOME/.local/bin/xfwm-titleless-maximized\"; [ -x \"$H\" ] || H=\"$HOME/DotCortex/linux/.local/bin/xfwm-titleless-maximized\"; \"$H\" status")))

(task 'xfwm:titleless-on
      "Hide titlebars/borders on maximized windows (panel carries the chrome)"
      (lambda ()
        (sh "H=\"$HOME/.local/bin/xfwm-titleless-maximized\"; [ -x \"$H\" ] || H=\"$HOME/DotCortex/linux/.local/bin/xfwm-titleless-maximized\"; \"$H\" enable")))

(task 'xfwm:titleless-off
      "Restore normal decorations on maximized windows"
      (lambda ()
        (sh "H=\"$HOME/.local/bin/xfwm-titleless-maximized\"; [ -x \"$H\" ] || H=\"$HOME/DotCortex/linux/.local/bin/xfwm-titleless-maximized\"; \"$H\" disable")))

;; --- Logseq ---
(task 'logseq:launch "Launch Logseq DB (starts ttyd if needed)"
      (lambda () (sh "logseq-db")))

(task 'logseq:api "Check Logseq HTTP API connectivity"
      (lambda () (sh "logseq-api check")))

(task 'logseq:tangle "Tangle logseq.org — launcher, plugin, API script"
      (lambda () (sh (string-append "tangle-one " HOME "/DotCortex/logseq.org"))))

;; --- Cargo ---
   (task 'cargo:capture "Capture live cargo to DotCortex SSV"
         (lambda () (sh "~/.local/bin/cargo-capture")))

   (task 'cargo:diff "Plan: manifest vs live cargo"
         (lambda () (sh "~/.local/bin/cargo-diff")))

   (task 'cargo:sync
         "Install or update only, no removals"
         (lambda () (sh "ENFORCE=0 UNINSTALL=0 UPDATE=1 ~/.local/bin/cargo-apply")))

   (task 'cargo:apply
         "Enforce exact cargo state, allow removals"
         (lambda () (sh "ENFORCE=1 UNINSTALL=1 UPDATE=1 ~/.local/bin/cargo-apply")))

   (task 'cargo:health "Show DotCortex Rust env and versions"
         (lambda () (sh "~/.local/bin/cargo-health")))

   ;; Build on a remote host in an ABI-matched container, verify, then install.
   ;; For hosts that cannot survive a local rustc storm -- see package-cargo.org.
   (task 'cargo:remote-apply
         "Build manifest on CARGO_BUILD_HOST, verify ABI, install here"
         (lambda () (sh "~/.local/bin/cargo-remote-apply")))

   ;; --- Fleet documentation library (sanctuary-docs.org) ---
   (task 'docs:build
         "Build Zeal docsets for this machine (host + sanctuary man corpora)"
         (lambda () (sh "~/.local/bin/dotcortex-docs-build")))

   (task 'docs:clean
         "Remove all generated docsets"
         (lambda () (sh "rm -rf ~/.local/share/dotcortex/docsets")))

   ;; --- Homebrew ---
   (task 'brew:apply
         "Enforce Homebrew state from DotCortex manifest"
         (lambda ()
           (sh "ENFORCE=1 UNINSTALL=1 UPDATE=1 ~/.local/bin/brew-apply")))

   (task 'brew:health
         "Show Homebrew env and install it if missing"
         (lambda ()
           (sh "~/.local/bin/brew-health")))

   ;; --- Apps (binary installers like kitty) ---
   (task 'app:apply
         "Apply app manifest (e.g. kitty upstream installer)"
         (lambda ()
           (sh "~/.local/bin/app-apply")))

    (task 'app:health
          "Check app level installs (kitty etc)"
          (lambda ()
            (sh "~/.local/bin/app-health")))

    ;; --- Bun ---
    (task 'bun:capture "Capture live Bun globals to DotCortex SSV"
          (lambda () (sh "~/.local/bin/bun-capture")))

    (task 'bun:diff "Plan: manifest vs live Bun globals"
          (lambda () (sh "~/.local/bin/bun-diff")))

    (task 'bun:sync
          "Install or update only, no removals"
          (lambda () (sh "ENFORCE=0 UNINSTALL=0 UPDATE=1 ~/.local/bin/bun-apply")))

    (task 'bun:apply
          "Enforce exact Bun global state, allow removals"
          (lambda () (sh "ENFORCE=1 UNINSTALL=1 UPDATE=1 ~/.local/bin/bun-apply")))

     (task 'bun:health "Show DotCortex Bun env and versions"
           (lambda () (sh "~/.local/bin/bun-health")))

     ;; --- Bunx ---
     (task 'bunx:capture "Capture managed bunx launchers to DotCortex SSV"
           (lambda () (sh "~/.local/bin/bunx-capture")))

    (task 'bunx:diff "Plan: manifest vs managed bunx launchers"
          (lambda () (sh "~/.local/bin/bunx-diff")))

    (task 'bunx:sync
          "Create or update managed bunx launchers, no removals"
          (lambda () (sh "ENFORCE=0 UNINSTALL=0 ~/.local/bin/bunx-apply")))

    (task 'bunx:apply
          "Enforce managed bunx launcher set, allow removals"
          (lambda () (sh "ENFORCE=1 UNINSTALL=1 ~/.local/bin/bunx-apply")))

    (task 'bunx:health "Show DotCortex bunx launcher state"
          (lambda () (sh "~/.local/bin/bunx-health")))

    ;; --- Node ---
    (task 'npm:capture "Capture live npm to DotCortex SSV"
          (lambda () (sh "~/.local/bin/npm-capture")))

   (task 'npm:diff "Plan: manifest vs live npm"
         (lambda () (sh "~/.local/bin/npm-diff")))

   (task 'npm:sync
         "Install or update only, no removals"
         (lambda () (sh "ENFORCE=0 UNINSTALL=0 UPDATE=1 ~/.local/bin/npm-apply")))

   (task 'npm:update
         "Install missing and update outdated packages, no removals"
         (lambda () (sh "ENFORCE=1 UNINSTALL=0 UPDATE=1 ~/.local/bin/npm-apply")))

   (task 'npm:apply
         "Enforce exact npm state, allow removals"
         (lambda () (sh "ENFORCE=1 UNINSTALL=1 UPDATE=1 ~/.local/bin/npm-apply")))

   (task 'npm:health "Show DotCortex Node env and versions"
         (lambda () (sh "~/.local/bin/npm-health")))

   ;; --- Fonts ---
   (task 'fonts:triage
         "Move bulky NerdFont variants + OpenType extras out of overlay to ~/.local/share/fonts/{NerdFontExtra,OpenTypeExtra}"
         (lambda ()
           (sh "~/.local/bin/fonts-nerdfont-extra-triage && ~/.local/bin/fonts-opentype-extra-triage")))

   (task 'fonts:cache "Rebuild fontconfig cache"
         (lambda () (sh "fc-cache -f")))

   ;; --- Pip ---
   (task 'pip:capture "Capture live pip to DotCortex SSV"
         (lambda () (sh "~/.local/bin/pip-capture")))

   (task 'pip:diff "Plan: manifest vs live pip"
         (lambda () (sh "~/.local/bin/pip-diff")))

   (task 'pip:apply
         "Install missing pip packages from manifest"
         (lambda () (sh "~/.local/bin/pip-apply")))

   (task 'pip:health "Show DotCortex Python/pip env and versions"
         (lambda () (sh "~/.local/bin/pip-health")))

   ;; --- HelmCortex shims (see helmcortex-shims.org) ---
   ;; capture needs the mount; apply and diff work from the local cache without it.
   (task 'hx:capture "Scan HelmCortex FORGE bins and write the shim manifest"
         (lambda () (sh "~/.local/bin/hx-capture")))

   (task 'hx:apply "Generate local HelmCortex shims from the manifest"
         (lambda () (sh "~/.local/bin/hx-apply")))

   (task 'hx:diff "Plan: manifest vs generated shims vs live HelmCortex"
         (lambda () (sh "~/.local/bin/hx-diff")))

   ;; --- Nala / apt ---
   (task 'nala:repos "Ensure third-party apt repos are configured"
         (lambda () (sh "make nala-repos")))

   (task 'nala:capture "Capture live apt manual packages to DotCortex SSV"
         (lambda () (sh "~/.local/bin/nala-capture")))

    (task 'nala:diff "Plan: manifest vs live apt packages"
          (lambda () (sh "~/.local/bin/nala-diff")))

    (task 'nala:release-diff
          "Plan: GitHub release-backed .deb packages"
          (lambda () (sh "make nala-release-diff")))

    (task 'nala:apply "Enforce nala manifest and release-backed .deb installs"
          (lambda () (sh "make nala-apply")))

    (task 'nala:apply-auto
          "Same as nala:apply but never prompts (agent/CI sessions with no TTY)"
          (lambda () (sh "make nala-apply-auto")))

   (task 'nala:health "Show nala/apt/dpkg status"
         (lambda () (sh "~/.local/bin/nala-health")))

   ;; --- DNF / OpenMandriva ---
   (task 'dnf:capture "Capture live DNF user-installed packages to DotCortex SSV"
         (lambda () (sh "~/.local/bin/dnf-capture")))

   (task 'dnf:diff "Plan: manifest vs live RPM packages"
         (lambda () (sh "~/.local/bin/dnf-diff")))

   (task 'dnf:sync
         "Install missing DNF packages without distro-sync first"
         (lambda () (sh "make dnf-sync")))

   (task 'dnf:apply
         "Distro-sync then install OpenMandriva DNF manifest packages"
         (lambda () (sh "make dnf-apply")))

   (task 'dnf:sonicde-xlibre
         "Install SonicDE and XLibre with --allowerasing"
         (lambda () (sh "make dnf-sonicde-xlibre")))

   (task 'dnf:health "Show DNF/RPM status"
         (lambda () (sh "~/.local/bin/dnf-health")))

   ;; --- Termux (Android) ---
   (task 'termux-pkg:apply
         "Install Termux packages from manifest"
         (lambda () (sh "~/.local/bin/termux-pkg-apply")))

   (task 'termux-pkg:health "Show Termux package environment"
         (lambda () (sh "~/.local/bin/termux-pkg-health")))

   ;; --- GitHub release artifacts ---
   ;; --- Backup ---
   (task 'backup:system
         "Clean + mirror system to ironwolf02 (needs sudo)"
         (lambda ()
           (run-sequential
            "sudo $HOME/.local/bin/backup-system-clean -y"
            "sudo $HOME/.local/bin/backup-system -y")))

   (task 'backup:dotcortex
         "Mirror ~/DotCortex to ironwolf02 (or push to X230 from T480s)"
         (lambda () (sh "$HOME/.local/bin/backup-dotcortex -y")))

   (task 'backup:nextcloud
         "Dual sync Nextcloud to ZFS pool + ironwolf02"
         (lambda () (sh "backup-nextcloud --auto -y")))

   (task 'backup:helmcortex
         "Run HelmCortex sacred sync"
         (lambda () (sh "~/HelmCortex/FORGE/bin/helmcortex-sync")))

   (task 'backup:games
         "Mirror ~/Games to ironwolf01"
         (lambda () (sh "backup-games --auto -y")))

   (task 'backup:retropie
         "Mirror ~/RetroPie to ironwolf01"
         (lambda () (sh "backup-retropie --auto -y")))

   (task 'backup:dedupe
         "Hardlink deduplication (requires --root)"
         (lambda () (sh "echo 'Usage: backup-dedupe --root PATH [-n|-y]'")))

   (task 'backup:all
         "Run all backups sequentially"
         (lambda ()
           (run-sequential
            "sudo $HOME/.local/bin/backup-system-clean -y"
            "sudo $HOME/.local/bin/backup-system -y"
            "$HOME/.local/bin/backup-dotcortex -y"
            "$HOME/.local/bin/backup-nextcloud --auto -y"
            "~/HelmCortex/FORGE/bin/helmcortex-sync"
            "backup-games --auto -y"
            "backup-retropie --auto -y")))

   (task 'dotcortex:clean-backups
         "Move backup-like files out of DotCortex into a timestamped Downloads archive"
         (lambda ()
           (sh "~/.local/bin/dotcortex-clean-backups --auto -y")))

   ;; --- Tmux ---
   (task 'tmux:apply
         "Install TPM and tmux plugins (resurrect, continuum, yank)"
         (lambda () (sh "~/.local/bin/tmux-apply")))

   (task 'tmux:health
         "Show tmux, TPM, plugin, and resurrect state"
         (lambda () (sh "~/.local/bin/tmux-health")))

   (task 'mux:session
         "Launch fleet multiplexer picker (tmux/Zellij)"
         (lambda () (sh "~/.local/bin/mux-session")))

   ;; --- Agent sessions ---
   (task 'sessions:once
         "Collect one agent-sessiond telemetry snapshot"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/sessions.mk sessions-once")))

   (task 'sessions:watch
         "Run agent-sessiond telemetry scanner loop"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/sessions.mk sessions-watch")))

   (task 'sessions:status
         "Show latest agent-sessiond telemetry summary"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/sessions.mk sessions-status")))

   (task 'sessions:top
         "Render live agent process cockpit"
         (lambda () (sh "make -f ~/DotCortex/all/.mk/sessions.mk sessions-top")))

   ;; --- Pipx ---
   (task 'pipx:apply
         "Install missing pipx-isolated packages from manifest"
         (lambda () (sh "~/.local/bin/pipx-apply")))

   (task 'pipx:health "Show DotCortex pipx env and installed venvs"
         (lambda () (sh "~/.local/bin/pipx-health")))

   ;; --- Agent schema ---
   (task 'agents:apply "Tangle agent docs, skills, commands, and hooks"
         (lambda () (sh "~/DotCortex/all/.local/bin/agents-apply")))

   (task 'agents:health "Show agent docs and generated output roots"
         (lambda () (sh "printf 'AGENTS.md\n'; sed -n '1,12p' AGENTS.md; printf '\nCLAUDE.md\n'; sed -n '1,12p' CLAUDE.md; printf '\n.agents/skills\n'; find .agents/skills -maxdepth 2 -name SKILL.md | sort | sed -n '1,12p'; printf '\n.claude/skills\n'; find .claude/skills -maxdepth 2 -name SKILL.md | sort | sed -n '1,12p'")))

   ;; --- Claude Code ---
   (task 'claude:apply "Install Claude Code plugins from manifest"
         (lambda () (sh "~/.local/bin/claude-plugins-apply")))

   (task 'claude:health "Show installed Claude Code plugins vs manifest"
         (lambda () (sh "~/.local/bin/claude-plugins-health")))

   ))
;; --- Pretty printing for help ---

(define (pad-right s width)
  (let ((n (string-length s)))
    (if (>= n width)
        s
        (string-append s (make-string (- width n) #\space)))))

(define (task-name-str t)
  (symbol->string (task-name t)))

(define (print-group title pred)
  (let* ((ts (filter pred tasks))
         (ts (sort ts (lambda (a b)
                        (string<? (task-name-str a)
                                  (task-name-str b))))))
    (when (pair? ts)
      (format #t "~a~%" title)
      (for-each
       (lambda (t)
         (let ((nm (pad-right (task-name-str t) 22)))
           (format #t "  ~a ~a~%" nm (task-desc t))))
       ts)
      (newline))))

(define (print-groups)
  ;; Main = everything that is not namespaced
  (print-group "Main commands"
               (lambda (t)
                 (let ((nm (task-name-str t)))
                   (and (not (string-prefix? "guix:" nm))
                        (not (string-prefix? "flatpak:" nm))
                        (not (string-prefix? "snap:" nm))
                        (not (string-prefix? "appimage:" nm))
                        (not (string-prefix? "dnf:" nm))
                        (not (string-prefix? "cargo:" nm))
                        (not (string-prefix? "npm:" nm))
                        (not (string-prefix? "root:" nm))
                        (not (string-prefix? "stow:" nm))
                        (not (string-prefix? "redstone:" nm))
                        (not (string-prefix? "defaults:" nm))
                        (not (string-prefix? "tmux:" nm))
                        (not (string-prefix? "sessions:" nm))
                        (not (string-prefix? "backup:" nm))
                        (not (string-prefix? "git:" nm))
                        (not (string-prefix? "dotcortex:" nm))
                        (not (string-prefix? "codex:" nm))
                        (not (string-prefix? "agents:" nm))))))

  (print-group "Agent commands"
               (lambda (t)
                 (string-prefix? "agents:" (task-name-str t))))

  (print-group "Codex commands"
               (lambda (t)
                 (string-prefix? "codex:" (task-name-str t))))

  (print-group "Stow / dotfiles commands"
               (lambda (t)
                 (let ((nm (task-name-str t)))
                   (or (string=? nm "stow")
                       (string-prefix? "stow:" nm)))))

  (print-group "Desktop defaults commands"
               (lambda (t)
                 (string-prefix? "defaults:" (task-name-str t))))

  (print-group "Redstone 9X commands"
               (lambda (t)
                 (string-prefix? "redstone:" (task-name-str t))))

  (print-group "Gnu Guix commands"
               (lambda (t)
                 (string-prefix? "guix:" (task-name-str t))))

  (print-group "Flatpak commands"
               (lambda (t)
                 (string-prefix? "flatpak:" (task-name-str t))))

  (print-group "Snap commands"
               (lambda (t)
                 (string-prefix? "snap:" (task-name-str t))))

  (print-group "DNF / OpenMandriva commands"
               (lambda (t)
                 (string-prefix? "dnf:" (task-name-str t))))

  (print-group "AppImage commands"
               (lambda (t)
                 (string-prefix? "appimage:" (task-name-str t))))

  (print-group "Cargo commands"
               (lambda (t)
                 (string-prefix? "cargo:" (task-name-str t))))

  (print-group "npm commands"
               (lambda (t)
                 (string-prefix? "npm:" (task-name-str t))))

  (print-group "Root commands"
               (lambda (t)
                 (string-prefix? "root:" (task-name-str t))))

  (print-group "Tmux commands"
               (lambda (t)
                 (string-prefix? "tmux:" (task-name-str t))))

  (print-group "Sessions commands"
               (lambda (t)
                 (string-prefix? "sessions:" (task-name-str t))))

  (print-group "Backup commands"
               (lambda (t)
                 (string-prefix? "backup:" (task-name-str t))))

  (print-group "Git commands"
               (lambda (t)
                 (string-prefix? "git:" (task-name-str t))))

  (print-group "Git commands"
               (lambda (t)
                 (string-prefix? "git:" (task-name-str t))))

  (print-group "DotCortex commands"
               (lambda (t)
                 (string-prefix? "dotcortex:" (task-name-str t)))))

;; --- Help / Version ---

(define (usage)
  (display
"Usage: loom OPTION | COMMAND ARGS...
Run COMMAND with ARGS, if given.

  -h, --help            display this helpful text and exit
  -V, --version         display version information and exit

COMMAND must be one of the sub-commands listed below:

")
  (print-groups)
  (newline)
  (display
"Tip: run 'loom list' to see raw task names for scripting.
"))

(define (print-version)
  (display "QuickSilver Loom v0.1 (maak control plane)\n"))

;; --- Dispatch ---

(define (run name)
  (let ((t (find (lambda (t)
                   (eq? (task-name t) name))
                 tasks)))
    (if t
        ((task-thunk t))
        (begin
          (format #t "Unknown task: ~a\n" name)
          1))))

;; Strip a literal "--" and everything before it in ARGV
(define (drop-dashdash xs)
  (cond ((and (pair? xs) (string=? (car xs) "--"))
         (drop-dashdash (cdr xs)))
        (else xs)))

(define (main args)
  (let* ((rest (drop-dashdash (cdr args))))
    (match rest
      (()            (begin (usage) 0))
      (("-h")        (begin (usage) 0))
      (("--help")    (begin (usage) 0))
      (("-V")        (begin (print-version) 0))
      (("--version") (begin (print-version) 0))
      (("help")      (begin (usage) 0))
      (("list")      (run 'list))
      ((cmd . _more) (run (string->symbol cmd)))
      (_             (begin (usage) 1)))))
;; Maak control plane (Scheme, XDG-friendly):1 ends here
