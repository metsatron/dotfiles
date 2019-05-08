## 0.2 - Atom 1.19.0 support
* Fixed async editor.save() issue. No support for atom <1.19 from now on

## 0.1.4 - Atom 1.17.0 support
* Focus on tree view after ZZ or ZQ

## 0.1.2 - Vim mode plus support per realh's request
* Added fim mode plus support

## 0.1.0 - Initial Release
* Save and Close Text Editor by hitting ZZ in vim normal mode
* When last editor is closed the focus is activated on tree view if it exists
and cursor is on the currently selected item
* Non-Vim ZQ binding which acts like :q! (since ex-mode q doesn't restore focus
on the tree view)
* Doesn't require vim-mode (but why would you use this package then?)
* Doesn't require tree view to be enabled
