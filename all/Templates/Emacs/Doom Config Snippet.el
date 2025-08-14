;;; ~/.doom.d/config.el --- Doom Emacs user config -*- lexical-binding: t; -*-

;; Created: <DATE>
;; Author: <Your Name>

(after! some-package
  (setq some-package-option t))

(map! :leader
      :desc "My custom command"
      "m x" #'my-custom-command)

(defun my-custom-command ()
  "Describe what this command does."
  (interactive)
  (message "Custom command executed!"))

