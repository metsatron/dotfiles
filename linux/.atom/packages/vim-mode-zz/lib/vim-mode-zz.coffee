module.exports =
    activate: ->
        atom.commands.add('atom-text-editor', {
            'vim-mode-zz:close': => @close()
            'vim-mode-zz:saveAndClose': => @saveAndClose()
        })

    close: ->
        pack = atom.packages.activePackages['tree-view']
        treeView = pack?.mainModule.treeView

        selected = treeView?.selectedEntry()

        editor = atom.workspace.getActiveTextEditor()
        editor?.destroy()

        if treeView and !atom.workspace.getActivePane().getActiveItem()
            treeView.selectEntry(selected)
            treeView.focus()

    saveAndClose: ->
        editor = atom.workspace.getActiveTextEditor()
        if editor.getPath() and editor.isModified()
            editor.save().done(=> @close())
        else @close(editor)
