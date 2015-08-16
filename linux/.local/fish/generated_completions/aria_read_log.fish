# aria_read_log
# Autogenerated from man page /usr/share/man/man1/aria_read_log.1.gz
# using Deroffing man parser
complete -c aria_read_log -s a -l apply --description 'Apply log to tables: modifies tables! you shoul… [See Man Page]'
complete -c aria_read_log -l character-sets-dir --description 'Directory where character sets are.'
complete -c aria_read_log -s c -l check --description 'if --display-only, check if record is fully rea… [See Man Page]'
complete -c aria_read_log -s '#' -l 'debug[' --description 'Output debug log.  Often the argument is \'d:t:o,filename\'.'
complete -c aria_read_log -l force-crash --description 'Force crash after # recovery events.'
complete -c aria_read_log -s '?' -l help --description 'Display this help and exit.'
complete -c aria_read_log -s d -l display-only --description 'display brief info read from records\' header.'
complete -c aria_read_log -s e -l end-lsn --description 'Stop applying at this lsn.'
complete -c aria_read_log -s h -l aria-log-dir-path --description 'Path to the directory where to store transactional log.'
complete -c aria_read_log -s P -l page-buffer-size --description 'The size of the buffer used for index blocks for Aria tables.'
complete -c aria_read_log -s o -l start-from-lsn --description 'Start reading log from this lsn.'
complete -c aria_read_log -s C -l start-from-checkpoint --description 'Start applying from last checkpoint.'
complete -c aria_read_log -s s -l silent --description 'Print less information during apply/undo phase.'
complete -c aria_read_log -s T -l tables-to-redo --description 'List of tables sepearated with , that we should apply REDO on.'
complete -c aria_read_log -s t -l tmpdir --description 'Path for temporary files.'
complete -c aria_read_log -l translog-buffer-size --description 'The size of the buffer used for transaction log… [See Man Page]'
complete -c aria_read_log -s u -l undo --description 'Apply UNDO records to tables.'
complete -c aria_read_log -s v -l verbose --description 'Print more information during apply/undo phase.'
complete -c aria_read_log -s V -l version --description 'Print version and exit.'
complete -c aria_read_log -l print-defaults --description 'Print the program argument list and exit.'
complete -c aria_read_log -l no-defaults --description 'Don\'t read default options from any option file.'
complete -c aria_read_log -l defaults-file --description 'Only read default options from the given file #.'
complete -c aria_read_log -l 'disable-undo)' --description '(Defaults to on; use --skip-undo to disable. ).'
complete -c aria_read_log -l defaults-extra-file --description 'Read this file after the global files are read.'

