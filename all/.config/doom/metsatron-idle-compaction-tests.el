;;; metsatron-idle-compaction-tests.el --- governor fixtures -*- lexical-binding: t; -*-
;; Canonical source: emacs-doom.org.  Regenerate this payload with
;; `tangle-one emacs-doom.org`; do not edit the tangled file in the overlay.
(require 'ert)
(load-file (expand-file-name "metsatron-idle-compaction.el"
                            (file-name-directory (or load-file-name
                                                      default-directory))))

(defun metsatron/idle-test--claude-state (tokens)
  "Return a fake Claude state with TOKENS in the status snapshot."
  (list :channel "claude-test"
        :buffer (generate-new-buffer " *idle-claude-test*")
        :process 'fake-process :session-id "claude-session"
        :status "idle" :enabled t :cache-profile 'long :dirty t
        :compacting nil :timer nil :timer-generation 0
        :last-local-keyboard-at nil
        :last-normal-turn-completed-at (- (float-time) 10)
        :active-input-context-tokens tokens
        :test-snapshot `((channel . "claude-test")
                         (session_id . "claude-session")
                         (current_input_context_tokens . ,tokens))))

(defun metsatron/idle-test--codex-bindings (session)
  "Return temporary Codex SESSION metadata bindings."
  (let ((metadata (make-hash-table :test #'eq)))
    (list
     (lambda (s key) (when (eq s session) (gethash key metadata)))
     (lambda (s key value)
       (when (eq s session) (puthash key value metadata))
       value))))

(defun metsatron/idle-test--kill-buffer (buffer)
  "Kill BUFFER without invoking the process query hook used by live vterm."
  (let ((kill-buffer-query-functions nil))
    (kill-buffer buffer)))

(ert-deftest metsatron/idle-claude-default-is-absolute-threshold ()
  (should (= claude-idle-compact-min-tokens 70000))
  (should (= claude-idle-compact-min-tokens 70000))
  (should (equal (metsatron/claude-idle-compact--profile-values 'long)
                 (list claude-idle-compact-seconds
                       claude-idle-compact-long-cache-ttl-seconds))))

(ert-deftest metsatron/idle-claude-below-threshold-does-not-compact ()
  (let ((state (metsatron/idle-test--claude-state 69999))
        (requests 0))
    (puthash "claude-test" state metsatron/claude-idle-compact--sessions)
    (cl-letf (((symbol-function 'metsatron/claude-idle-compact--snapshot)
               (lambda (_state) (plist-get state :test-snapshot)))
              ((symbol-function 'metsatron/claude-idle-compact--vterm-draft-present-p)
               (lambda () nil))
              ((symbol-function 'process-live-p) (lambda (_process) t))
              ((symbol-function 'get-buffer-process) (lambda (_buffer) 'fake-process))
              ((symbol-function 'codex-ide--terminal-send-string)
               (lambda (&rest _args) (setq requests (1+ requests))))
              ((symbol-function 'claude-code-ide--terminal-send-string)
               (lambda (&rest _args) (setq requests (1+ requests))))
              ((symbol-function 'claude-code-ide--terminal-send-return)
               (lambda (&rest _args) nil)))
      (metsatron/claude-idle-compact--attempt state)
      (should (= requests 0))
      (metsatron/idle-test--kill-buffer (plist-get state :buffer)))))

(ert-deftest metsatron/idle-claude-at-threshold-compacts-with-million-window ()
  (let ((state (metsatron/idle-test--claude-state 70000))
        (requests 0))
    (puthash "claude-test" state metsatron/claude-idle-compact--sessions)
    (cl-letf (((symbol-function 'metsatron/claude-idle-compact--snapshot)
               (lambda (_state) (plist-get state :test-snapshot)))
              ((symbol-function 'metsatron/claude-idle-compact--vterm-draft-present-p)
               (lambda () nil))
              ((symbol-function 'process-live-p) (lambda (_process) t))
              ((symbol-function 'get-buffer-process) (lambda (_buffer) 'fake-process))
              ((symbol-function 'claude-code-ide--terminal-send-string)
               (lambda (&rest _args) (setq requests (1+ requests))))
              ((symbol-function 'claude-code-ide--terminal-send-return)
               (lambda (&rest _args) nil))
              ((symbol-function 'derived-mode-p) (lambda (&rest _modes) t)))
      (metsatron/claude-idle-compact--attempt state)
      (should (= requests 1))
      (should (plist-get (gethash "claude-test"
                                  metsatron/claude-idle-compact--sessions)
                         :compacting))
      (metsatron/idle-test--kill-buffer (plist-get state :buffer)))))

(ert-deftest metsatron/idle-claude-expired-timer-skips ()
  (let ((state (metsatron/idle-test--claude-state 80000))
        (requests 0))
    (setq state (plist-put state :last-normal-turn-completed-at
                           (- (float-time) claude-idle-compact-long-cache-ttl-seconds 1)))
    (puthash "claude-test" state metsatron/claude-idle-compact--sessions)
    (cl-letf (((symbol-function 'metsatron/claude-idle-compact--snapshot)
               (lambda (_state) (plist-get state :test-snapshot)))
              ((symbol-function 'metsatron/claude-idle-compact--vterm-draft-present-p)
               (lambda () nil))
              ((symbol-function 'process-live-p) (lambda (_process) t))
              ((symbol-function 'get-buffer-process) (lambda (_buffer) 'fake-process))
              ((symbol-function 'claude-code-ide--terminal-send-string)
               (lambda (&rest _args) (setq requests (1+ requests))))
              ((symbol-function 'claude-code-ide--terminal-send-return)
               (lambda (&rest _args) nil))
              ((symbol-function 'derived-mode-p) (lambda (&rest _modes) t)))
      (metsatron/claude-idle-compact--attempt state)
      (should (= requests 0))
      (metsatron/idle-test--kill-buffer (plist-get state :buffer)))))

(ert-deftest metsatron/idle-claude-post-compact-clears-dirty-and-tokens ()
  (let ((state (metsatron/idle-test--claude-state 80000)))
    (puthash "claude-test" state metsatron/claude-idle-compact--sessions)
    (metsatron/claude-idle-compact-handle-hook
     'post-compact "claude-test" "claude-session")
    (setq state (gethash "claude-test" metsatron/claude-idle-compact--sessions))
    (should-not (plist-get state :dirty))
    (should-not (plist-get state :compacting))
    (should-not (plist-get state :active-input-context-tokens))
    (metsatron/idle-test--kill-buffer (plist-get state :buffer))))

(ert-deftest metsatron/idle-claude-compaction-stop-does-not-rearm ()
  (let ((state (metsatron/idle-test--claude-state 80000)))
    (setq state (plist-put state :compacting t))
    (puthash "claude-test" state metsatron/claude-idle-compact--sessions)
    (metsatron/claude-idle-compact-handle-hook
     'stop "claude-test" "claude-session")
    (setq state (gethash "claude-test" metsatron/claude-idle-compact--sessions))
    (should (plist-get state :compacting))
    (should (plist-get state :dirty))
    (should-not (plist-get state :timer))
    (metsatron/idle-test--kill-buffer (plist-get state :buffer))))

(ert-deftest metsatron/idle-codex-token-fixture-uses-last-total ()
  (let* ((session 'codex-session)
         (metadata (make-hash-table :test #'eq))
         (get (lambda (_s key) (gethash key metadata)))
         (put (lambda (_s key value) (puthash key value metadata))))
    (cl-letf (((symbol-function 'codex-ide--session-metadata-get) get)
              ((symbol-function 'codex-ide--session-metadata-put) put)
              ((symbol-function 'codex-ide-session-thread-id) (lambda (_s) "thread-1"))
              ((symbol-function 'codex-ide-session-process) (lambda (_s) 'process))
              ((symbol-function 'codex-ide-session-buffer) (lambda (_s) nil))
              ((symbol-function 'codex-ide-session-status) (lambda (_s) "idle")))
      (metsatron/codex-idle-compact--handle-notification
       (lambda (&rest _args) nil) session
       '((method . "thread/tokenUsage/updated")
         (params . ((threadId . "thread-1")
                    (turnId . "turn-1")
                    (tokenUsage .
                     ((total . ((totalTokens . 900000)))
                      (last . ((inputTokens . 70000)
                               (cachedInputTokens . 12000)
                               (cacheWriteInputTokens . 1000)
                               (totalTokens . 83000)))
                      (modelContextWindow . 1000000)))))))
      (should (= (plist-get (gethash metsatron/codex-idle-compact--metadata-key
                                     metadata)
                            :current-context-tokens)
                 83000)))))

(ert-deftest metsatron/idle-codex-turn-fixture-uses-owning-session ()
  (let* ((session 'codex-session)
         (metadata (make-hash-table :test #'eq))
         (get (lambda (_s key) (gethash key metadata)))
         (put (lambda (_s key value) (puthash key value metadata)))
         (timers 0))
    (cl-letf (((symbol-function 'codex-ide--session-metadata-get) get)
              ((symbol-function 'codex-ide--session-metadata-put) put)
              ((symbol-function 'codex-ide-session-thread-id) (lambda (_s) "thread-1"))
              ((symbol-function 'codex-ide-session-process) (lambda (_s) 'process))
              ((symbol-function 'codex-ide-session-buffer) (lambda (_s) 'buffer))
              ((symbol-function 'codex-ide-session-status) (lambda (_s) "idle"))
              ((symbol-function 'process-live-p) (lambda (_p) t))
              ((symbol-function 'buffer-live-p) (lambda (_b) t))
              ((symbol-function 'run-at-time)
               (lambda (&rest _args) (setq timers (1+ timers)) 'timer))
              ((symbol-function 'timerp) (lambda (_timer) t))
              ((symbol-function 'cancel-timer) (lambda (_timer) nil)))
      (metsatron/codex-idle-compact--handle-notification
       (lambda (&rest _args) nil) session
       '((method . "turn/completed")
         (params . ((turn . ((id . "turn-1") (status . "completed") (items . nil)))))))
      (should (plist-get (gethash metsatron/codex-idle-compact--metadata-key
                                  metadata)
                         :dirty))
      (should (= timers 1)))))

(ert-deftest metsatron/idle-codex-duplicate-idle-does-not-arm-twice ()
  (let* ((session 'codex-session)
         (metadata (make-hash-table :test #'eq))
         (get (lambda (_s key) (gethash key metadata)))
         (put (lambda (_s key value) (puthash key value metadata)))
         (timers 0))
    (puthash metsatron/codex-idle-compact--metadata-key
             (list :session session :thread-id "thread-1" :connection 'process
                   :owning-buffer 'buffer :status "idle" :enabled t :dirty t
                   :compacting nil :timer nil :timer-generation 0
                   :last-normal-turn-completed-at (- (float-time) 10)
                   :current-context-tokens 80000)
             metadata)
    (cl-letf (((symbol-function 'codex-ide--session-metadata-get) get)
              ((symbol-function 'codex-ide--session-metadata-put) put)
              ((symbol-function 'codex-ide-session-thread-id) (lambda (_s) "thread-1"))
              ((symbol-function 'codex-ide-session-process) (lambda (_s) 'process))
              ((symbol-function 'codex-ide-session-buffer) (lambda (_s) 'buffer))
              ((symbol-function 'process-live-p) (lambda (_p) t))
              ((symbol-function 'buffer-live-p) (lambda (_b) t))
              ((symbol-function 'run-at-time)
               (lambda (&rest _args) (setq timers (1+ timers)) 'timer))
              ((symbol-function 'timerp) (lambda (_timer) t))
              ((symbol-function 'cancel-timer) (lambda (_timer) nil)))
      (metsatron/codex-idle-compact--arm session)
      (metsatron/codex-idle-compact--arm session)
      (should (= timers 1)))))

(ert-deftest metsatron/idle-codex-draft-and-active-gates-block ()
  (let* ((session 'codex-session)
         (metadata (make-hash-table :test #'eq))
         (get (lambda (_s key) (gethash key metadata)))
         (put (lambda (_s key value) (puthash key value metadata)))
         (requests 0))
    (puthash metsatron/codex-idle-compact--metadata-key
             (list :session session :thread-id "thread-1" :connection 'process
                   :owning-buffer 'buffer :status "active" :enabled t :dirty t
                   :compacting nil :last-normal-turn-completed-at (- (float-time) 10)
                   :current-context-tokens 80000)
             metadata)
    (cl-letf (((symbol-function 'codex-ide--session-metadata-get) get)
              ((symbol-function 'codex-ide--session-metadata-put) put)
              ((symbol-function 'codex-ide-session-thread-id) (lambda (_s) "thread-1"))
              ((symbol-function 'codex-ide--session-for-thread-id) (lambda (_id) session))
              ((symbol-function 'codex-ide--current-input-empty-p) (lambda (_s) nil))
              ((symbol-function 'codex-ide-session-process) (lambda (_s) 'process))
              ((symbol-function 'codex-ide-session-buffer) (lambda (_s) 'buffer))
              ((symbol-function 'process-live-p) (lambda (_p) t))
              ((symbol-function 'buffer-live-p) (lambda (_b) t))
              ((symbol-function 'codex-ide--request-async)
               (lambda (&rest _args) (setq requests (1+ requests))))
              ((symbol-function 'timerp) (lambda (_timer) t))
              ((symbol-function 'cancel-timer) (lambda (_timer) nil)))
      (metsatron/codex-idle-compact--attempt session)
      (should (= requests 0))
      (metsatron/codex-idle-compact--put session :status "idle")
      (metsatron/codex-idle-compact--attempt session)
      (should (= requests 0)))))

(ert-deftest metsatron/idle-codex-compaction-completion-cleans-without-loop ()
  (let* ((session 'codex-session)
         (metadata (make-hash-table :test #'eq))
         (get (lambda (_s key) (gethash key metadata)))
         (put (lambda (_s key value) (puthash key value metadata))))
    (puthash metsatron/codex-idle-compact--metadata-key
             (list :session session :thread-id "thread-1" :connection 'process
                   :owning-buffer 'buffer :status "idle" :enabled t :dirty t
                   :compacting t :timer nil :last-normal-turn-completed-at
                   (- (float-time) 10) :current-context-tokens 80000)
             metadata)
    (cl-letf (((symbol-function 'codex-ide--session-metadata-get) get)
              ((symbol-function 'codex-ide--session-metadata-put) put)
              ((symbol-function 'codex-ide-session-thread-id) (lambda (_s) "thread-1"))
      ((symbol-function 'codex-ide-session-process) (lambda (_s) 'process))
              ((symbol-function 'codex-ide-session-buffer) (lambda (_s) 'buffer))
              ((symbol-function 'codex-ide-session-status) (lambda (_s) "idle")))
      (metsatron/codex-idle-compact--handle-notification
       (lambda (&rest _args) nil) session
       '((method . "item/started")
         (params . ((item . ((id . "item-1")
                             (type . "contextCompaction")))))))
      (metsatron/codex-idle-compact--handle-notification
       (lambda (&rest _args) nil) session
       '((method . "item/completed")
         (params . ((item . ((id . "item-1")
                             (type . "contextCompaction")
                             (status . "completed")))))))
      (metsatron/codex-idle-compact--handle-notification
       (lambda (&rest _args) nil) session
       '((method . "turn/completed")
         (params . ((turn . ((id . "turn-2") (status . "completed")
                             (items . (((type . "contextCompaction"))))))))))
      (let ((state (gethash metsatron/codex-idle-compact--metadata-key metadata)))
        (should-not (plist-get state :dirty))
        (should-not (plist-get state :compacting))))))

(ert-deftest metsatron/idle-codex-stale-timer-cannot-request ()
  (let* ((session 'codex-session)
         (metadata (make-hash-table :test #'eq))
         (get (lambda (_s key) (gethash key metadata)))
         (put (lambda (_s key value) (puthash key value metadata)))
         (requests 0))
    (puthash metsatron/codex-idle-compact--metadata-key
             (list :session session :thread-id "thread-new" :connection 'process
                   :owning-buffer 'buffer :status "idle" :enabled t :dirty t
                   :compacting nil :timer-generation 2
                   :last-normal-turn-completed-at 200 :current-context-tokens 80000)
             metadata)
    (cl-letf (((symbol-function 'codex-ide--session-metadata-get) get)
              ((symbol-function 'codex-ide--session-metadata-put) put)
              ((symbol-function 'codex-ide--request-async)
               (lambda (&rest _args) (setq requests (1+ requests)))))
      (metsatron/codex-idle-compact--timer-fired session "thread-old" 100 1)
      (should (= requests 0)))))

(ert-deftest metsatron/idle-claude-local-input-cancels-pending-timer ()
  (let ((state (metsatron/idle-test--claude-state 80000)))
    (setq state (plist-put state :timer 'pending-timer))
    (puthash "claude-test" state metsatron/claude-idle-compact--sessions)
    (with-current-buffer (plist-get state :buffer)
      (metsatron/claude-idle-compact--local-activity))
    (setq state (gethash "claude-test" metsatron/claude-idle-compact--sessions))
    (should-not (plist-get state :timer))
    (should (numberp (plist-get state :last-local-keyboard-at)))
    (should (equal (plist-get state :last-cancellation-reason) "user-input"))
    (metsatron/idle-test--kill-buffer (plist-get state :buffer))))

(ert-deftest metsatron/idle-claude-later-turn-rearms-after-successful-compact ()
  (let ((state (metsatron/idle-test--claude-state 80000))
        (timers 0))
    (puthash "claude-test" state metsatron/claude-idle-compact--sessions)
    (cl-letf (((symbol-function 'process-live-p) (lambda (_process) t))
              ((symbol-function 'run-at-time)
               (lambda (&rest _args) (setq timers (1+ timers)) 'timer))
              ((symbol-function 'timerp) (lambda (_timer) t))
              ((symbol-function 'cancel-timer) (lambda (_timer) nil)))
      (metsatron/claude-idle-compact-handle-hook
       'stop "claude-test" "claude-session")
      (should (= timers 1))
      (metsatron/claude-idle-compact-handle-hook
       'post-compact "claude-test" "claude-session")
      (setq state (gethash "claude-test" metsatron/claude-idle-compact--sessions))
      (should-not (plist-get state :dirty))
      (should-not (plist-get state :timer))
      (metsatron/claude-idle-compact-handle-hook
       'stop "claude-test" "claude-session")
      (should (= timers 2)))
    (metsatron/idle-test--kill-buffer (plist-get state :buffer))))

(ert-deftest metsatron/idle-codex-eligible-session-requests-once ()
  (let* ((session 'codex-session)
         (metadata (make-hash-table :test #'eq))
         (get (lambda (_s key) (gethash key metadata)))
         (put (lambda (_s key value) (puthash key value metadata)))
         (requests 0))
    (puthash metsatron/codex-idle-compact--metadata-key
             (list :session session :thread-id "thread-1" :connection 'process
                   :owning-buffer 'buffer :status "idle" :enabled t :dirty t
                   :compacting nil :timer nil
                   :last-normal-turn-completed-at (- (float-time) 10)
                   :current-context-tokens 80000 :prompt-draft-dirty nil)
             metadata)
    (cl-letf (((symbol-function 'codex-ide--session-metadata-get) get)
              ((symbol-function 'codex-ide--session-metadata-put) put)
              ((symbol-function 'codex-ide-session-thread-id)
               (lambda (_s) "thread-1"))
              ((symbol-function 'codex-ide-session-process)
               (lambda (_s) 'process))
              ((symbol-function 'codex-ide-session-buffer)
               (lambda (_s) 'buffer))
              ((symbol-function 'process-live-p) (lambda (_p) t))
              ((symbol-function 'buffer-live-p) (lambda (_b) t))
              ((symbol-function 'codex-ide--request-async)
               (lambda (&rest _args) (setq requests (1+ requests)))))
      (metsatron/codex-idle-compact--attempt session)
      (should (= requests 1))
      (should (plist-get (gethash metsatron/codex-idle-compact--metadata-key
                                  metadata)
                         :compacting)))))

(ert-deftest metsatron/idle-codex-sessions-are-isolated ()
  (let ((metadata (make-hash-table :test #'eq)))
    (dolist (session '(one two))
      (puthash session (list :session session :thread-id (symbol-name session)
                             :connection 'process :owning-buffer 'buffer
                             :status "idle" :enabled t :dirty nil)
               metadata))
    (should-not (plist-get (gethash 'one metadata) :dirty))
    (should-not (plist-get (gethash 'two metadata) :dirty))))
