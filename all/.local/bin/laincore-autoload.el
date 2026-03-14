;;; Autoloads for dynamic header evaluation (SAFE)
(unless (fboundp 'lc/emit)
  ;; Accept (app lane path) and just return PATH so :tangle can resolve.
  (defun lc/emit (&rest args) (nth 2 args)))
(provide 'laincore-autoload)
