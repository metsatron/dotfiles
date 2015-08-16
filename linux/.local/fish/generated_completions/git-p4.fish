# git-p4
# Autogenerated from man page /usr/share/man/man1/git-p4.1.gz
# using Deroffing man parser
complete -c git-p4 -l git-dir --description 'Set the GIT_DIR environment variable.  See git(1).'
complete -c git-p4 -s v -l verbose --description 'Provide more progress information.'
complete -c git-p4 -l branch --description 'Import changes into <ref> instead of refs/remotes/p4/master.'
complete -c git-p4 -l detect-branches --description 'Use the branch detection algorithm to find new paths in p4.'
complete -c git-p4 -l changesfile --description 'Import exactly the p4 change numbers listed in … [See Man Page]'
complete -c git-p4 -l silent --description 'Do not print any progress information.'
complete -c git-p4 -l detect-labels --description 'Query p4 for labels associated with the depot p… [See Man Page]'
complete -c git-p4 -l import-labels --description 'Import labels from p4 into Git.'
complete -c git-p4 -l import-local --description 'By default, p4 branches are stored in refs/remo… [See Man Page]'
complete -c git-p4 -l max-changes --description 'Limit the number of imported changes to n.'
complete -c git-p4 -l keep-path --description 'The mapping of file names from the p4 depot pat… [See Man Page]'
complete -c git-p4 -l use-client-spec --description 'Use a client spec to find the list of interesting files in p4.'
complete -c git-p4 -s / --description 'Exclude selected depot paths when cloning or syncing.'
complete -c git-p4 -l destination --description 'Where to create the Git repository.'
complete -c git-p4 -l bare --description 'Perform a bare clone.  See git-clone(1).'
complete -c git-p4 -l origin --description 'Upstream location from which commits are identi… [See Man Page]'
complete -c git-p4 -s M --description 'Detect renames.  See git-diff(1).'
complete -c git-p4 -l preserve-user --description 'Re-author p4 changes before submitting to p4.'
complete -c git-p4 -l export-labels --description 'Export tags from Git as p4 labels.'
complete -c git-p4 -s n -l dry-run --description 'Show just what commits would be submitted to p4… [See Man Page]'
complete -c git-p4 -l prepare-p4-only --description 'Apply a commit to the p4 workspace, opening, ad… [See Man Page]'
complete -c git-p4 -l conflict --description 'Conflicts can occur when applying a commit to p4.'
complete -c git-p4 -s u --description 'P4USER can be used instead.  git-p4. password.'
complete -c git-p4 -s P --description 'P4PASS can be used instead.  git-p4. port.'
complete -c git-p4 -s p --description 'P4PORT can be used instead.  git-p4. host.'
complete -c git-p4 -s h --description 'P4HOST can be used instead.  git-p4. client.'
complete -c git-p4 -s c --description '.'
complete -c git-p4 -l 'use-client-spec.' --description '.'

