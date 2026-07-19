#!/usr/bin/python3
#
# CDE / Motif Theme for XFCE & GTK
# Copyright (C) 2026 Arthur Clark (netrunner01)
# Based on the CDE/Motif theme by Jos van Riswick, used with permission.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#find out how get sass working
#/*version 4 - GTK 4.x*/
import re
import os
with open('widgets.jos.css') as f:lines=f.read().splitlines() 
#with open('widgets.jos.1.css') as f:lines=f.read().splitlines() 

print('process...')
print(os.getcwd())

dialog='dialog'
messagedialog='messagedialog'
popover='popover'
viewport='viewport'
treeview='treeview'
menu='menu'
button='button'
entry='entry'
label='label'
window='window'

print('GTK 4.x')

with open('widgets.css', 'w') as f: 

    #these are the normal defs
    for l in lines:
        m=re.sub('_dialog','',l)
        m=re.sub('_borderwidth','1px',m)
        f.write(m)
        f.write('/n')

    f.write("""/* Portion for green pop messagedialog ********************* *//n """)

    #these are the same ones inside a dialog
    for l in lines:
        m=re.sub('_dialog',messagedialog,l)
        m=re.sub('bg_gen','bg_menu',m)
        m=re.sub('ts_gen','ts_menu',m)
        m=re.sub('bs_gen','bs_menu',m)
        m=re.sub('sel_gen','sel_menu',m)
        m=re.sub('fg_gen','fg_menu',m)
        m=re.sub('_borderwidth','1px',m)
        m=re.sub('colorset5','colorset6',m)
        f.write(m)
        f.write('/n')

    f.write("""/* Portion for treeview ********************* *//n """)

    #these are the same ones inside popover
    for l in lines:
        m=re.sub('_dialog',treeview,l)
        m=re.sub('bg_gen','bg_text',m)
        m=re.sub('ts_gen','ts_text',m)
        m=re.sub('bs_gen','bs_text',m)
        m=re.sub('sel_gen','sel_text',m)
        m=re.sub('fg_gen','fg_text',m)
        m=re.sub('_borderwidth','1px',m)
        m=re.sub('colorset5','colorset4',m)
        #green combobut inside tree stays green
        #########m=re.sub('colorset6','colorset4',m)
        f.write(m)
        f.write('/n')

    f.write("""/* Portion for green pop popover ********************* *//n """)

    #these are the same ones inside popover
    for l in lines:
        m=re.sub('_dialog',popover,l)
        m=re.sub('bg_gen','bg_menu',m)
        m=re.sub('ts_gen','ts_menu',m)
        m=re.sub('bs_gen','bs_menu',m)
        m=re.sub('sel_gen','sel_menu',m)
        m=re.sub('fg_gen','fg_menu',m)
        m=re.sub('_borderwidth','1px',m)
        m=re.sub('colorset5','colorset6',m)
        f.write(m)
        f.write('/n')

    f.write("""/* Portion for green pop up dialogs ********************* *//n """)

    for l in lines:
        m=re.sub('_dialog',dialog,l)
        m=re.sub('bg_gen','bg_menu',m)
        m=re.sub('ts_gen','ts_menu',m)
        m=re.sub('bs_gen','bs_menu',m)
        m=re.sub('sel_gen','sel_menu',m)
        m=re.sub('fg_gen','fg_menu',m)
        m=re.sub('_borderwidth','1px',m)
        m=re.sub('colorset5','colorset6',m)
        f.write(m)
        f.write('/n')

    f.write("""/* Portion for green pop up menu ********************* *//n """)

    #this actually works haha
    #but mainly for menu disabled text shadow maybe just put it in the css file
    #widget.css gets kindof long like this (13000)
    for l in lines:
        m=re.sub('_dialog',menu,l)
        m=re.sub('bg_gen','bg_menu',m)
        m=re.sub('ts_gen','ts_menu',m)
        m=re.sub('bs_gen','bs_menu',m)
        m=re.sub('sel_gen','sel_menu',m)
        m=re.sub('fg_gen','fg_menu',m)
        m=re.sub('bg_text','bg_menu',m)
        m=re.sub('ts_text','ts_menu',m)
        m=re.sub('bs_text','bs_menu',m)
        m=re.sub('sel_text','sel_menu',m)
        m=re.sub('fg_text','fg_menu',m)
        m=re.sub('_borderwidth','1px',m)
        m=re.sub('colorset5','colorset6',m)
        f.write(m)
        f.write('/n')

    f.write(m)
    f.write('/n')

