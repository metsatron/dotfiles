;;; metsatron-idle-compaction.el --- idle prompt-cache compaction -*- lexical-binding: t; -*-
;; Canonical source: emacs-doom.org.  Regenerate this payload with
;; `tangle-one emacs-doom.org`; do not edit the tangled file in the overlay.

(require 'cl-lib)
(require 'json)
(require 'subr-x)

;; Protocol/package declarations are intentionally soft: Doom may load this
;; file before either IDE package, but byte compilation should still document
;; the exact optional entry points used by the live integration.
(declare-function claude-code-ide--terminal-send-string "claude-code-ide"
                  (string))
(declare-function claude-code-ide--terminal-send-return "claude-code-ide" ())
(declare-function codex-ide-session-thread-id "codex-ide-session" (session))
(declare-function codex-ide-session-process "codex-ide-session" (session))
(declare-function codex-ide-session-buffer "codex-ide-session" (session))
(declare-function codex-ide-session-status "codex-ide-session" (session))
(declare-function codex-ide--session-metadata-get "codex-ide-session"
                  (session key))
(declare-function codex-ide--session-metadata-put "codex-ide-session"
                  (session key value))
(declare-function codex-ide--session-for-thread-id "codex-ide-session"
                  (thread-id &optional directory))
(declare-function codex-ide--request-async "codex-ide-session"
                  (session method params callback))

(defgroup metsatron-idle-compaction nil
  "Idle prompt-cache compaction for Claude and Codex IDE sessions."
  :group 'tools)

(defcustom metsatron-idle-compaction-enabled t
  "Whether idle compaction is enabled globally."
  :type 'boolean :group 'metsatron-idle-compaction)

(defcustom metsatron-idle-compaction-debug nil
  "Whether to log idle-compaction state transitions."
  :type 'boolean :group 'metsatron-idle-compaction)

(defcustom claude-idle-compact-seconds (* 55 60)
  "Idle delay before cache-harvest compaction for one-hour Claude caches."
  :type 'integer :group 'metsatron-idle-compaction)

(defcustom claude-short-cache-idle-compact-seconds (* 4 60)
  "Idle delay before compaction for short-lived Claude prompt caches."
  :type 'integer :group 'metsatron-idle-compaction)

(defcustom claude-idle-compact-min-tokens 70000
  "Minimum active Claude input-context tokens before idle compaction."
  :type 'integer :group 'metsatron-idle-compaction)

(defcustom claude-idle-compact-long-cache-ttl-seconds (* 60 60)
  "Assumed warm-cache TTL for the Claude long-cache profile."
  :type 'integer :group 'metsatron-idle-compaction)

(defcustom claude-idle-compact-short-cache-ttl-seconds (* 5 60)
  "Warm-cache TTL for the Claude short-cache profile."
  :type 'integer :group 'metsatron-idle-compaction)

(defcustom claude-idle-compact-cache-profile 'auto
  "Default Claude prompt-cache profile for new sessions.
`auto' only recognizes explicit environment flags and never guesses a dynamic
subscription/usage-credit TTL."
  :type '(choice (const long) (const short) (const auto))
  :group 'metsatron-idle-compaction)

(defcustom codex-idle-compact-seconds (* 27 60)
  "Initial idle delay before Codex cache-harvest compaction."
  :type 'integer :group 'metsatron-idle-compaction)

(defcustom codex-cache-ttl-seconds (* 30 60)
  "Assumed warm-cache TTL for Codex idle compaction.
The app-server protocol does not expose the authenticated backend's retention
policy, so this remains configurable."
  :type 'integer :group 'metsatron-idle-compaction)

(defcustom codex-idle-compact-min-tokens 70000
  "Minimum Codex current context usage tokens before idle compaction."
  :type 'integer :group 'metsatron-idle-compaction)

(defcustom metsatron-idle-compaction-emacs-server "doom"
  "Named Emacs server used by Claude hook helpers."
  :type 'string :group 'metsatron-idle-compaction)

(defvar metsatron/claude-idle-compact--sessions (make-hash-table :test #'equal)
  "Claude idle-compaction state keyed by the unique launch channel.")

(defconst metsatron/codex-idle-compact--metadata-key
  :metsatron-idle-compaction
  "Codex session metadata key for governor state.")

(defun metsatron/idle-compaction--now ()
  "Return the wall-clock timestamp used by idle-compaction state."
  (float-time))

(defun metsatron/idle-compaction--short-id (value)
  "Return a safe truncated representation of VALUE for debug logging."
  (let ((text (format "%s" (or value "unknown"))))
    (if (> (length text) 12) (concat (substring text 0 8) "…") text)))

(defun metsatron/idle-compaction--log (kind id format-string &rest args)
  "Log KIND and safe ID when debugging is enabled.
FORMAT-STRING and ARGS must not contain prompt or authentication data."
  (when metsatron-idle-compaction-debug
    (apply #'message
           (concat "[idle-compact " (symbol-name kind) " "
                   (metsatron/idle-compaction--short-id id) "] "
                   format-string)
           args)))

(defun metsatron/idle-compaction--cancel-timer (timer)
  "Cancel TIMER when it is a live Emacs timer."
  (when (timerp timer) (cancel-timer timer)))

(defun metsatron/claude-idle-compact--effective-profile (&optional profile)
  "Resolve PROFILE to `long' or `short'.
The `auto' case uses only explicit environment flags."
  (let ((profile (or profile claude-idle-compact-cache-profile)))
    (if (memq profile '(long short))
        profile
      (cond
       ((member (getenv "FORCE_PROMPT_CACHING_5M") '("1" "true" "TRUE"))
        'short)
       ((member (getenv "ENABLE_PROMPT_CACHING_1H") '("1" "true" "TRUE"))
        'long)
       (t 'long)))))

(defun metsatron/claude-idle-compact--profile-values (profile)
  "Return `(DELAY TTL)' for Claude PROFILE."
  (if (eq (metsatron/claude-idle-compact--effective-profile profile) 'short)
      (list claude-short-cache-idle-compact-seconds
            claude-idle-compact-short-cache-ttl-seconds)
    (list claude-idle-compact-seconds claude-idle-compact-long-cache-ttl-seconds)))

(defun metsatron/claude-idle-compact--state-profile (state)
  "Return the effective per-session Claude cache profile for STATE."
  (or (plist-get state :effective-profile)
      (metsatron/claude-idle-compact--effective-profile
       (plist-get state :cache-profile))))

(defun metsatron/claude-idle-compact--state (channel)
  "Return Claude state for CHANNEL."
  (gethash channel metsatron/claude-idle-compact--sessions))

(defun metsatron/claude-idle-compact--put (channel key value)
  "Set KEY to VALUE in Claude CHANNEL state and return the state."
  (when-let ((state (metsatron/claude-idle-compact--state channel)))
    (setq state (plist-put state key value))
    (puthash channel state metsatron/claude-idle-compact--sessions)
    state))

(defun metsatron/claude-idle-compact--current-state (&optional buffer)
  "Return the Claude state owning BUFFER, or the current buffer."
  (setq buffer (or buffer (current-buffer)))
  (catch 'state
    (maphash (lambda (_channel state)
               (when (eq buffer (plist-get state :buffer))
                 (throw 'state state)))
             metsatron/claude-idle-compact--sessions)
    nil))

(defun metsatron/claude-idle-compact--cancel (state reason)
  "Cancel STATE's pending timer with REASON."
  (when state
    (let* ((channel (plist-get state :channel))
           (generation (1+ (or (plist-get state :timer-generation) 0))))
      (metsatron/idle-compaction--cancel-timer (plist-get state :timer))
      (setq state (plist-put state :timer nil))
      (setq state (plist-put state :timer-generation generation))
      (setq state (plist-put state :last-cancellation-reason reason))
      (puthash channel state metsatron/claude-idle-compact--sessions)
      (metsatron/idle-compaction--log 'cancelled channel "reason=%s" reason)
      state)))

(defun metsatron/claude-idle-compact--vterm-draft-present-p ()
  "Return non-nil when the current Claude vterm has unsent input.
Fail closed when the installed vterm does not expose its input accessor."
  (if (fboundp 'vterm--get-input)
      (condition-case _err
          (not (string-empty-p (string-trim (or (vterm--get-input) ""))))
        (error t))
    t))

(defun metsatron/claude-idle-compact--snapshot (state)
  "Read and validate the latest status-line snapshot for Claude STATE."
  (let* ((runtime (getenv "XDG_RUNTIME_DIR"))
         (channel (plist-get state :channel))
         (session-id (plist-get state :session-id))
         (path (and runtime
                    (expand-file-name
                     (format "claude-idle-compact-%s.json" channel) runtime))))
    (when (and path (file-readable-p path))
      (condition-case _err
          (let ((json-object-type 'alist)
                (json-array-type 'list)
                (json-key-type 'symbol))
            (let ((snapshot (json-read-file path)))
              (when (and (equal channel (alist-get 'channel snapshot))
                         (equal session-id (alist-get 'session_id snapshot))
                         (numberp (alist-get 'current_input_context_tokens snapshot)))
                snapshot)))
        (error nil)))))

(defun metsatron/claude-idle-compact--arm (state)
  "Arm one Claude idle timer for STATE when lifecycle permits it."
  (when (and state metsatron-idle-compaction-enabled
             (plist-get state :enabled) (plist-get state :dirty)
             (equal (plist-get state :status) "idle")
             (not (plist-get state :compacting))
             (not (plist-get state :timer))
             (buffer-live-p (plist-get state :buffer))
             (process-live-p (plist-get state :process)))
    (let* ((channel (plist-get state :channel))
           (session-id (plist-get state :session-id))
           (completed-at (plist-get state :last-normal-turn-completed-at))
           (profile (metsatron/claude-idle-compact--state-profile state))
           (delay (car (metsatron/claude-idle-compact--profile-values profile)))
           (generation (1+ (or (plist-get state :timer-generation) 0)))
           (timer (run-at-time delay nil
                               #'metsatron/claude-idle-compact--timer-fired
                               channel session-id completed-at generation)))
      (metsatron/idle-compaction--cancel-timer (plist-get state :timer))
      (setq state (plist-put state :effective-profile profile))
      (setq state (plist-put state :timer-generation generation))
      (setq state (plist-put state :timer timer))
      (puthash channel state metsatron/claude-idle-compact--sessions)
      (metsatron/idle-compaction--log 'armed channel "profile=%s delay=%ss"
                                      profile delay)
      state)))

(defun metsatron/claude-idle-compact--timer-fired
    (channel session-id completed-at generation)
  "Run the atomic Claude gate for captured timer identity."
  (when-let ((state (metsatron/claude-idle-compact--state channel)))
    (when (and (= generation (plist-get state :timer-generation))
               (equal session-id (plist-get state :session-id))
               (equal completed-at (plist-get state :last-normal-turn-completed-at)))
      (metsatron/claude-idle-compact--put channel :timer nil)
      (metsatron/claude-idle-compact--attempt state))))

(defun metsatron/claude-idle-compact--attempt (state)
  "Run the complete Claude eligibility gate for STATE."
  (let* ((channel (plist-get state :channel))
         (buffer (plist-get state :buffer))
         (process (plist-get state :process))
         (completion (plist-get state :last-normal-turn-completed-at))
         (profile (metsatron/claude-idle-compact--state-profile state))
         (ttl (cadr (metsatron/claude-idle-compact--profile-values profile)))
         (elapsed (and completion (- (metsatron/idle-compaction--now) completion)))
         (snapshot (and (buffer-live-p buffer)
                        (process-live-p process)
                        (metsatron/claude-idle-compact--snapshot state)))
         (tokens (and snapshot
                      (alist-get 'current_input_context_tokens snapshot))))
    (when (numberp tokens)
      (setq state (metsatron/claude-idle-compact--put
                   channel :active-input-context-tokens tokens)))
    (cond
     ((not metsatron-idle-compaction-enabled)
      (metsatron/idle-compaction--log 'cancelled channel "globally-disabled"))
     ((not (plist-get state :enabled))
      (metsatron/idle-compaction--log 'cancelled channel "session-disabled"))
     ((not (plist-get state :dirty))
      (metsatron/idle-compaction--log 'cancelled channel "clean"))
     ((plist-get state :compacting)
      (metsatron/idle-compaction--log 'cancelled channel "already-compacting"))
     ((not (and (buffer-live-p buffer)
                (with-current-buffer buffer (derived-mode-p 'vterm-mode))))
      (metsatron/idle-compaction--log 'cancelled channel "buffer-not-vterm"))
     ((not (process-live-p process))
      (metsatron/idle-compaction--log 'cancelled channel "process-gone"))
     ((not (equal process (get-buffer-process buffer)))
      (metsatron/idle-compaction--log 'cancelled channel "process-replaced"))
     ((not completion)
      (metsatron/idle-compaction--log 'cancelled channel "no-completion-time"))
     ((or (null elapsed) (>= elapsed ttl))
      (metsatron/idle-compaction--log 'cancelled channel "cache-already-cold"))
     ((not snapshot)
      (metsatron/idle-compaction--log 'cancelled channel "missing-or-stale-status"))
     ((and (numberp (plist-get state :last-local-keyboard-at))
           (> (plist-get state :last-local-keyboard-at) completion))
      (metsatron/idle-compaction--log 'cancelled channel "user-input"))
     ((metsatron/claude-idle-compact--vterm-draft-present-p)
      (metsatron/idle-compaction--log 'cancelled channel "draft-present"))
     ((< (or tokens 0) claude-idle-compact-min-tokens)
      (metsatron/idle-compaction--log 'cancelled channel
                                      "below-token-threshold tokens=%s" tokens))
     (t
      (setq state (plist-put state :compacting t))
      (puthash channel state metsatron/claude-idle-compact--sessions)
      (metsatron/idle-compaction--log 'compaction-requested channel "Claude /compact")
      (condition-case _err
          (with-current-buffer buffer
            (claude-code-ide--terminal-send-string "/compact")
            (claude-code-ide--terminal-send-return))
        (error
         (setq state (plist-put state :compacting nil))
         (puthash channel state metsatron/claude-idle-compact--sessions)
         (metsatron/idle-compaction--log 'compaction-failed channel
                                         "synchronous submission failure")))))))

(defun metsatron/claude-idle-compact--local-activity ()
  "Cancel Claude idle compaction after local buffer activity."
  (when-let ((state (metsatron/claude-idle-compact--current-state)))
    (metsatron/claude-idle-compact--put
     (plist-get state :channel) :last-local-keyboard-at
     (metsatron/idle-compaction--now))
    (metsatron/claude-idle-compact--cancel state "user-input")))

(defun metsatron/claude-idle-compact--process-gone (channel process)
  "Cancel CHANNEL when PROCESS disappears."
  (when-let ((state (metsatron/claude-idle-compact--state channel)))
    (when (eq process (plist-get state :process))
      (metsatron/claude-idle-compact--cancel state "process-gone"))))

(defun metsatron/claude-idle-compact-register
    (channel buffer process &optional session-id)
  "Register a Claude CHANNEL owned by BUFFER and PROCESS."
  (when (and (stringp channel) (buffer-live-p buffer))
    (let ((state (list :channel channel :buffer buffer :process process
                       :session-id session-id :status "idle" :enabled t
                       :cache-profile claude-idle-compact-cache-profile
                       :effective-profile
                       (metsatron/claude-idle-compact--effective-profile
                        claude-idle-compact-cache-profile)
                       :dirty nil :compacting nil :timer nil
                       :timer-generation 0 :last-local-keyboard-at nil
                       :last-normal-turn-completed-at nil
                       :active-input-context-tokens nil
                       :last-cancellation-reason nil)))
      (puthash channel state metsatron/claude-idle-compact--sessions)
      (with-current-buffer buffer
        (add-hook 'pre-command-hook
                  #'metsatron/claude-idle-compact--local-activity nil t)
        (add-hook 'kill-buffer-hook
                  (lambda ()
                    (when-let ((current
                               (metsatron/claude-idle-compact--current-state)))
                      (metsatron/claude-idle-compact--cancel
                       current "buffer-unloaded")))
                  nil t))
      (when (processp process)
        (let ((old-sentinel (process-sentinel process)))
          (set-process-sentinel
           process
           (lambda (proc event)
             (when (functionp old-sentinel)
               (funcall old-sentinel proc event))
             (metsatron/claude-idle-compact--process-gone channel proc)))))
      state)))

(defun metsatron/claude-idle-compact-handle-hook
    (event channel session-id)
  "Handle validated Claude hook EVENT for CHANNEL and SESSION-ID.
This function is called only by `claude-hook-idle-event'."
  (when-let ((state (metsatron/claude-idle-compact--state channel)))
    (when (or (null (plist-get state :session-id))
              (equal session-id (plist-get state :session-id)))
      (setq state (plist-put state :session-id session-id))
      (pcase event
       ('stop
         (if (plist-get state :compacting)
             (progn
               ;; A /compact command can also produce Stop.  It is not a new
               ;; ordinary turn: leave `compacting' set until PostCompact so
               ;; this notification can never create an idle loop.
               (setq state (plist-put state :status "idle"))
               (puthash channel state metsatron/claude-idle-compact--sessions)
               (metsatron/claude-idle-compact--cancel state "compaction-stop"))
           (setq state (plist-put state :status "idle"))
           (setq state (plist-put state :dirty t))
           (setq state (plist-put state :last-normal-turn-completed-at
                                  (metsatron/idle-compaction--now)))
           (puthash channel state metsatron/claude-idle-compact--sessions)
           (metsatron/claude-idle-compact--cancel state "new-normal-turn")
           (metsatron/claude-idle-compact--arm state)))
        ('user-prompt-submit
         (setq state (plist-put state :status "active"))
         (metsatron/claude-idle-compact--cancel state "prompt-submit"))
        ('post-compact
         (setq state (plist-put state :status "idle"))
         (setq state (plist-put state :dirty nil))
         (setq state (plist-put state :compacting nil))
         (setq state (plist-put state :active-input-context-tokens nil))
         (puthash channel state metsatron/claude-idle-compact--sessions)
         (metsatron/claude-idle-compact--cancel state "compaction-completed")
         (metsatron/idle-compaction--log 'compaction-completed channel "Claude"))
        ('session-activity
         (setq state (plist-put state :status "active"))
         (puthash channel state metsatron/claude-idle-compact--sessions)
         (metsatron/claude-idle-compact--cancel state "session-active"))
        ((or 'stop-failure 'session-end)
         (setq state (plist-put state :status (symbol-name event)))
         (puthash channel state metsatron/claude-idle-compact--sessions)
         (metsatron/claude-idle-compact--cancel state (symbol-name event)))))))

(defun metsatron/claude-idle-compact-set-profile (profile)
  "Set the current Claude session cache PROFILE and re-arm its timer.
PROFILE is one of `long', `short', or `auto'."
  (interactive
   (list (intern (completing-read "Claude cache profile: "
                                  '("long" "short" "auto") nil t))))
  (let ((state (metsatron/claude-idle-compact--current-state)))
    (unless state (user-error "The current buffer is not a Claude IDE session"))
    (setq state (plist-put state :cache-profile profile))
    (setq state (plist-put state :effective-profile
                           (metsatron/claude-idle-compact--effective-profile
                            profile)))
    (puthash (plist-get state :channel) state metsatron/claude-idle-compact--sessions)
    (metsatron/claude-idle-compact--cancel state "profile-changed")
    (metsatron/claude-idle-compact--arm state)
    (message "Claude idle-compaction profile: %s (effective %s)"
             profile (metsatron/claude-idle-compact--effective-profile profile))))

(defun metsatron/codex-idle-compact--state (session)
  "Return or initialize governor state for Codex SESSION."
  (when (and session (fboundp 'codex-ide--session-metadata-get))
    (or (codex-ide--session-metadata-get
         session metsatron/codex-idle-compact--metadata-key)
        (let ((state (list :session session
                           :thread-id (codex-ide-session-thread-id session)
                           :connection (codex-ide-session-process session)
                           :owning-buffer (codex-ide-session-buffer session)
                           :status (or (codex-ide-session-status session) "idle")
                           :timer nil :timer-generation 0 :enabled t
                           :dirty nil :compacting nil
                           :last-normal-turn-completed-at nil
                           :last-local-input-at nil
                           :current-context-tokens nil
                           :context-window-size nil
                           :prompt-draft-dirty nil
                           :compaction-item-completed nil
                           :compaction-failed nil
                           :last-cancellation-reason nil)))
          (codex-ide--session-metadata-put
           session metsatron/codex-idle-compact--metadata-key state)
          state))))

(defun metsatron/codex-idle-compact--put (session key value)
  "Set Codex SESSION state KEY to VALUE and return the state."
  (when-let ((state (metsatron/codex-idle-compact--state session)))
    (setq state (plist-put state key value))
    (codex-ide--session-metadata-put
     session metsatron/codex-idle-compact--metadata-key state)
    state))

(defun metsatron/codex-idle-compact--cancel (session reason)
  "Cancel the Codex SESSION timer with REASON."
  (when-let ((state (metsatron/codex-idle-compact--state session)))
    (metsatron/idle-compaction--cancel-timer (plist-get state :timer))
    (setq state (plist-put state :timer nil))
    (setq state (plist-put state :timer-generation
                           (1+ (or (plist-get state :timer-generation) 0))))
    (setq state (plist-put state :last-cancellation-reason reason))
    (codex-ide--session-metadata-put
     session metsatron/codex-idle-compact--metadata-key state)
    (metsatron/idle-compaction--log 'cancelled
                                    (plist-get state :thread-id)
                                    "reason=%s" reason)
    state))

(defun metsatron/codex-idle-compact--arm (session)
  "Arm one Codex idle timer for SESSION when it is eligible to wait."
  (when-let ((state (metsatron/codex-idle-compact--state session)))
    (when (and metsatron-idle-compaction-enabled
               (plist-get state :enabled)
               (plist-get state :dirty)
               (equal (plist-get state :status) "idle")
               (not (plist-get state :compacting))
               (not (plist-get state :timer))
               (process-live-p (plist-get state :connection))
               (buffer-live-p (plist-get state :owning-buffer)))
      (let* ((thread-id (plist-get state :thread-id))
             (completion (plist-get state :last-normal-turn-completed-at))
             (generation (1+ (or (plist-get state :timer-generation) 0)))
             (timer (run-at-time codex-idle-compact-seconds nil
                                 #'metsatron/codex-idle-compact--timer-fired
                                 session thread-id completion generation)))
        (metsatron/idle-compaction--cancel-timer (plist-get state :timer))
        (setq state (plist-put state :timer-generation generation))
        (setq state (plist-put state :timer timer))
        (codex-ide--session-metadata-put
         session metsatron/codex-idle-compact--metadata-key state)
        (metsatron/idle-compaction--log 'armed thread-id
                                        "Codex delay=%ss" codex-idle-compact-seconds)
        state))))

(defun metsatron/codex-idle-compact--timer-fired
    (session thread-id completion generation)
  "Run the atomic Codex gate for captured timer identity."
  (when-let ((state (metsatron/codex-idle-compact--state session)))
    (when (and (= generation (plist-get state :timer-generation))
               (equal thread-id (plist-get state :thread-id))
               (equal completion (plist-get state :last-normal-turn-completed-at)))
      (metsatron/codex-idle-compact--put session :timer nil)
      (metsatron/codex-idle-compact--attempt session))))

(defun metsatron/codex-idle-compact--draft-present-p (session)
  "Return non-nil when Codex SESSION has unsent or queued prompt input."
  (or (and (fboundp 'codex-ide--current-input-empty-p)
           (condition-case _err
               (not (codex-ide--current-input-empty-p session))
             (wrong-number-of-arguments
              (not (codex-ide--current-input-empty-p)))))
      (and (fboundp 'codex-ide-session-prompt-history-draft)
           (let ((draft (codex-ide-session-prompt-history-draft session)))
             (and (stringp draft) (not (string-empty-p (string-trim draft))))))
      (and (plist-get (metsatron/codex-idle-compact--state session)
                      :prompt-draft-dirty)
           t)
      (and (fboundp 'codex-ide-session-input-prompt-start-marker)
           (fboundp 'codex-ide-session-mode--input-end-position)
           (let* ((buffer (codex-ide-session-buffer session))
                  (start (codex-ide-session-input-prompt-start-marker session))
                  (end (codex-ide-session-mode--input-end-position session))
                  (end-position (if (markerp end) (marker-position end) end)))
             (and (buffer-live-p buffer)
                  (markerp start)
                  (integer-or-marker-p end)
                  (eq (marker-buffer start) buffer)
                  (integer-or-marker-p end-position)
                  (< (marker-position start) end-position)
                  (with-current-buffer buffer
                    (let ((draft (string-trim
                                  (buffer-substring-no-properties
                                   (marker-position start)
                                   end-position))))
                      (not (string-empty-p
                            (string-remove-prefix "> " draft))))))))
      ;; Older local builds used this metadata slot for queued prompts.  Keep
      ;; the fallback harmless and session-local when present.
      (and (fboundp 'codex-ide--session-metadata-get)
           (codex-ide--session-metadata-get session :queued-prompts))))

(defun metsatron/codex-idle-compact--owned-p (session thread-id)
  "Return non-nil when THREAD-ID is still owned by SESSION."
  (and (equal thread-id (codex-ide-session-thread-id session))
       (or (not (fboundp 'codex-ide--session-for-thread-id))
           (eq session (codex-ide--session-for-thread-id thread-id)))))

(defun metsatron/codex-idle-compact--attempt (session)
  "Run the complete Codex eligibility gate for SESSION."
  (when-let ((state (metsatron/codex-idle-compact--state session)))
    (let* ((thread-id (plist-get state :thread-id))
           (connection (plist-get state :connection))
           (buffer (plist-get state :owning-buffer))
           (completion (plist-get state :last-normal-turn-completed-at))
           (elapsed (and completion (- (metsatron/idle-compaction--now) completion)))
           (tokens (plist-get state :current-context-tokens)))
      (cond
       ((not metsatron-idle-compaction-enabled)
        (metsatron/idle-compaction--log 'cancelled thread-id "globally-disabled"))
       ((not (plist-get state :enabled))
        (metsatron/idle-compaction--log 'cancelled thread-id "session-disabled"))
       ((not (equal (plist-get state :status) "idle"))
        (metsatron/idle-compaction--log 'cancelled thread-id "session-active"))
       ((not (plist-get state :dirty))
        (metsatron/idle-compaction--log 'cancelled thread-id "clean"))
       ((plist-get state :compacting)
        (metsatron/idle-compaction--log 'cancelled thread-id "already-compacting"))
       ((not (process-live-p connection))
        (metsatron/idle-compaction--log 'cancelled thread-id "connection-gone"))
       ((not (buffer-live-p buffer))
        (metsatron/idle-compaction--log 'cancelled thread-id "buffer-unloaded"))
       ((not (metsatron/codex-idle-compact--owned-p session thread-id))
        (metsatron/idle-compaction--log 'cancelled thread-id "thread-replaced"))
       ((metsatron/codex-idle-compact--draft-present-p session)
        (metsatron/idle-compaction--log 'cancelled thread-id "draft-present"))
       ((or (null elapsed) (>= elapsed codex-cache-ttl-seconds))
        (metsatron/idle-compaction--log 'cancelled thread-id "cache-already-cold"))
       ((< (or tokens 0) codex-idle-compact-min-tokens)
        (metsatron/idle-compaction--log 'cancelled thread-id
                                        "below-token-threshold tokens=%s" tokens))
       (t
        (setq state (plist-put state :compacting t))
        (codex-ide--session-metadata-put
         session metsatron/codex-idle-compact--metadata-key state)
        (metsatron/idle-compaction--log 'compaction-requested thread-id
                                        "Codex thread/compact/start")
        (condition-case _err
            (codex-ide--request-async
             session "thread/compact/start"
             `((threadId . ,thread-id))
             (lambda (_result error)
               (when error
                 (metsatron/codex-idle-compact--put session :compacting nil)
                 (metsatron/idle-compaction--log
                  'compaction-failed thread-id "RPC request failed"))))
          (error
           (metsatron/codex-idle-compact--put session :compacting nil)
           (metsatron/idle-compaction--log
            'compaction-failed thread-id "synchronous request failure"))))))))

(defun metsatron/codex-idle-compact--local-activity ()
  "Cancel Codex idle compaction after local session-buffer activity."
  (when (and (derived-mode-p 'codex-ide-session-mode)
             (fboundp 'codex-ide--session-for-current-buffer))
    (when-let ((session (codex-ide--session-for-current-buffer)))
      (metsatron/codex-idle-compact--put
       session :last-local-input-at (metsatron/idle-compaction--now))
      (metsatron/codex-idle-compact--put session :prompt-draft-dirty t)
      (metsatron/codex-idle-compact--cancel session "user-input"))))

(defun metsatron/codex-idle-compact--handle-notification
    (original session message)
  "Observe raw Codex app-server MESSAGE for owning SESSION.
The owning session, not an optional raw `threadId' field, is authoritative for
turn/completed ownership because the README and generated schema differ."
  (let* ((method (alist-get 'method message))
         (params (alist-get 'params message))
         (thread-id (and (listp params) (alist-get 'threadId params)))
         (state (and session (metsatron/codex-idle-compact--state session)))
         (owner-ok (and state
                        (or (null thread-id)
                            (equal thread-id (plist-get state :thread-id))))))
    (when (and state owner-ok (equal method "item/started"))
      (let ((item (alist-get 'item params)))
        (when (equal (alist-get 'type item) "contextCompaction")
          (metsatron/codex-idle-compact--put session :compacting t)
          (metsatron/codex-idle-compact--cancel session "compaction-started"))))
    (prog1 (if owner-ok (funcall original session message) nil)
      (when (and state owner-ok)
        (cond
         ((equal method "thread/status/changed")
          (let* ((raw-status (or (alist-get 'status params)
                                 (alist-get 'status (alist-get 'thread params))))
                 (type (if (stringp raw-status)
                           raw-status
                         (alist-get 'type raw-status))))
            (metsatron/codex-idle-compact--put session :status type)
            (if (equal type "idle")
                (metsatron/codex-idle-compact--arm session)
              (metsatron/codex-idle-compact--cancel
               session (if (equal type "active") "session-active" type)))))
         ((equal method "thread/tokenUsage/updated")
          (let* ((usage (alist-get 'tokenUsage params))
                 (last (alist-get 'last usage))
                 ;; This is Codex's current context usage metric.  The
                 ;; cumulative `tokenUsage.total.totalTokens' is deliberately
                 ;; not used for the eligibility threshold.
                 (tokens (alist-get 'totalTokens last))
                 (window (alist-get 'modelContextWindow usage)))
            (metsatron/codex-idle-compact--put
             session :current-context-tokens tokens)
            (metsatron/codex-idle-compact--put
             session :context-window-size window)))
         ((equal method "item/started")
          (let ((item (alist-get 'item params)))
            (when (equal (alist-get 'type item) "contextCompaction")
              (metsatron/codex-idle-compact--put
               session :compaction-item-completed nil)
              (metsatron/codex-idle-compact--put
               session :compaction-failed nil))))
         ((equal method "item/completed")
          (let* ((item (alist-get 'item params))
                 (type (alist-get 'type item))
                 (status (alist-get 'status item)))
            (when (equal type "contextCompaction")
              (if (member status '("failed" "interrupted" "error"))
                  (progn
                    (metsatron/codex-idle-compact--put
                     session :compaction-failed t)
                    (metsatron/codex-idle-compact--put
                     session :compacting nil)
                    (metsatron/idle-compaction--log
                     'compaction-failed (plist-get state :thread-id)
                     "item status=%s" status))
                (metsatron/codex-idle-compact--put
                 session :compaction-item-completed t)
                (metsatron/codex-idle-compact--put
                 session :compacting nil)))))
         ((equal method "turn/completed")
          (let* ((turn (alist-get 'turn params))
                 (status (alist-get 'status turn))
                 (items (alist-get 'items turn))
                 (compaction (or (plist-get state :compacting)
                                 (plist-get state :compaction-item-completed)
                                 (plist-get state :compaction-failed)
                                 (cl-some (lambda (item)
                                            (equal (alist-get 'type item)
                                                   "contextCompaction"))
                                          items))))
            (if compaction
                (progn
                  (metsatron/codex-idle-compact--put session :compacting nil)
                  (if (and (equal status "completed")
                           (not (plist-get state :compaction-failed)))
                      (progn
                        (metsatron/codex-idle-compact--put session :dirty nil)
                        (metsatron/idle-compaction--log
                         'compaction-completed (plist-get state :thread-id) "Codex"))
                    (metsatron/idle-compaction--log
                     'compaction-failed (plist-get state :thread-id)
                     "turn status=%s" status))
                  (metsatron/codex-idle-compact--put
                   session :compaction-item-completed nil)
                  (metsatron/codex-idle-compact--put
                   session :compaction-failed nil))
              (when (equal status "completed")
                (metsatron/codex-idle-compact--put session :dirty t)
                (metsatron/codex-idle-compact--put
                 session :last-normal-turn-completed-at
                 (metsatron/idle-compaction--now))
                (metsatron/codex-idle-compact--put session :prompt-draft-dirty nil)
                (metsatron/codex-idle-compact--arm session)))))
         ((equal method "error")
          (when (or (plist-get state :compacting)
                    (plist-get state :compaction-item-completed))
            (metsatron/codex-idle-compact--put session :compacting nil)
            (metsatron/codex-idle-compact--put session :compaction-failed t)
            (metsatron/idle-compaction--log
             'compaction-failed (plist-get state :thread-id) "app-server error"))))))))

(defun metsatron/codex-idle-compact--install-session-buffer ()
  "Install Codex local-input and process cleanup hooks for current session."
  (when (fboundp 'codex-ide--session-for-current-buffer)
    (when-let* ((session (codex-ide--session-for-current-buffer))
                (process (codex-ide-session-process session)))
      (add-hook 'pre-command-hook
                #'metsatron/codex-idle-compact--local-activity nil t)
      (unless (process-get process 'metsatron-codex-idle-compact-sentinel)
        (process-put process 'metsatron-codex-idle-compact-sentinel t)
        (let ((old-sentinel (process-sentinel process)))
          (set-process-sentinel
           process
           (lambda (proc event)
             (when (functionp old-sentinel)
               (funcall old-sentinel proc event))
             (ignore event)
             (metsatron/codex-idle-compact--cancel session "connection-gone"))))))))

(defun metsatron/idle-compaction--current-codex-session ()
  "Return the Codex session owning the current buffer, if any."
  (and (fboundp 'codex-ide--session-for-current-buffer)
       (codex-ide--session-for-current-buffer)))

(defun metsatron/idle-compaction--current-state ()
  "Return the current Claude or Codex governor state."
  (or (metsatron/claude-idle-compact--current-state)
      (when-let ((session (metsatron/idle-compaction--current-codex-session)))
        (metsatron/codex-idle-compact--state session))))

(defun metsatron/idle-compaction-enable ()
  "Enable idle compaction globally."
  (interactive)
  (setq metsatron-idle-compaction-enabled t)
  (message "Idle compaction enabled globally"))

(defun metsatron/idle-compaction-disable ()
  "Disable idle compaction globally and cancel all pending timers."
  (interactive)
  (setq metsatron-idle-compaction-enabled nil)
  (maphash (lambda (_channel state)
             (metsatron/claude-idle-compact--cancel state "globally-disabled"))
           metsatron/claude-idle-compact--sessions)
  (when (boundp 'codex-ide--sessions)
    (dolist (session codex-ide--sessions)
      (metsatron/codex-idle-compact--cancel session "globally-disabled")))
  (message "Idle compaction disabled globally"))

(defun metsatron/idle-compaction-enable-session ()
  "Enable idle compaction for the current Claude or Codex session."
  (interactive)
  (let ((state (metsatron/idle-compaction--current-state)))
    (unless state (user-error "No Claude or Codex IDE session owns this buffer"))
    (if (plist-get state :channel)
        (progn
          (setq state (plist-put state :enabled t))
          (puthash (plist-get state :channel) state
                   metsatron/claude-idle-compact--sessions)
          (metsatron/claude-idle-compact--arm state))
      (let ((session (plist-get state :session)))
        (metsatron/codex-idle-compact--put session :enabled t)
        (metsatron/codex-idle-compact--arm session)))
    (message "Idle compaction enabled for current session")))

(defun metsatron/idle-compaction-disable-session ()
  "Disable idle compaction for the current Claude or Codex session."
  (interactive)
  (let ((state (metsatron/idle-compaction--current-state)))
    (unless state (user-error "No Claude or Codex IDE session owns this buffer"))
    (if (plist-get state :channel)
        (progn
          (setq state (plist-put state :enabled nil))
          (puthash (plist-get state :channel) state
                   metsatron/claude-idle-compact--sessions)
          (metsatron/claude-idle-compact--cancel state "session-disabled"))
      (let ((session (plist-get state :session)))
        (metsatron/codex-idle-compact--put session :enabled nil)
        (metsatron/codex-idle-compact--cancel session "session-disabled")))
    (message "Idle compaction disabled for current session")))

(defun metsatron/idle-compaction-cancel-current ()
  "Cancel the current session's pending idle-compaction timer."
  (interactive)
  (let ((state (metsatron/idle-compaction--current-state)))
    (unless state (user-error "No Claude or Codex IDE session owns this buffer"))
    (if (plist-get state :channel)
        (metsatron/claude-idle-compact--cancel state "manual-cancel")
      (metsatron/codex-idle-compact--cancel
       (plist-get state :session) "manual-cancel"))))

(defun metsatron/idle-compaction-show-state ()
  "Display safe idle-compaction state for the current agent session."
  (interactive)
  (let ((state (metsatron/idle-compaction--current-state)))
    (unless state (user-error "No Claude or Codex IDE session owns this buffer"))
    (when (plist-get state :channel)
      (when-let ((snapshot (metsatron/claude-idle-compact--snapshot state)))
        (setq state
              (metsatron/claude-idle-compact--put
               (plist-get state :channel)
               :active-input-context-tokens
               (alist-get 'current_input_context_tokens snapshot)))))
    (let* ((claude (plist-get state :channel))
           (completion (plist-get state :last-normal-turn-completed-at))
           (profile (and claude
                          (metsatron/claude-idle-compact--state-profile state)))
           (values (and claude
                         (metsatron/claude-idle-compact--profile-values profile)))
           (ttl (if claude (cadr values) codex-cache-ttl-seconds))
           (threshold (if claude claude-idle-compact-min-tokens
                        codex-idle-compact-min-tokens))
           (tokens (plist-get state (if claude :active-input-context-tokens
                                      :current-context-tokens))))
      (message "%s id=%s status=%s dirty=%s compacting=%s tokens=%s threshold=%s completion=%s idle=%s ttl=%ss deadline=%s draft=%s cancelled=%s profile=%s delay=%ss"
               (if claude "Claude" "Codex")
               (or (plist-get state (if claude :session-id :thread-id)) "unknown")
               (plist-get state :status) (plist-get state :dirty)
               (plist-get state :compacting) (or tokens "unknown") threshold
               completion
               (and completion (- (metsatron/idle-compaction--now) completion))
               ttl (and completion (+ completion ttl))
               (if claude
                   (metsatron/claude-idle-compact--vterm-draft-present-p)
                 (metsatron/codex-idle-compact--draft-present-p
                  (plist-get state :session)))
               (plist-get state :last-cancellation-reason)
               profile (and claude (car values))))))

(defun metsatron/idle-compaction-trigger-current ()
  "Run the same validated idle-compaction gate for the current session."
  (interactive)
  (let ((state (metsatron/idle-compaction--current-state)))
    (unless state (user-error "No Claude or Codex IDE session owns this buffer"))
    (if (plist-get state :channel)
        (metsatron/claude-idle-compact--attempt state)
      (metsatron/codex-idle-compact--attempt (plist-get state :session)))))

(with-eval-after-load 'codex-ide
  (when (fboundp 'codex-ide--handle-notification)
    (advice-add 'codex-ide--handle-notification :around
                #'metsatron/codex-idle-compact--handle-notification))
  (add-hook 'codex-ide-session-mode-hook
            #'metsatron/codex-idle-compact--install-session-buffer))

(provide 'metsatron-idle-compaction)
;;; metsatron-idle-compaction.el ends here
