#!/usr/bin/python
# pyuic4 ui_ColorDialog.ui -o ui_ColorDialog.py
# 
# cb .jos https://github.com/mattrobenolt/colors.py/blob/master/colors/base.py
#
import sys
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)
from PyQt4 import QtGui,QtCore 
from PyQt4.QtCore import QString
import subprocess
import re
from functools import partial
from colors import hsv, hex
import Globals
#Qtdesigner file dont edit:
import ui_Help
import WorkspaceFuncs
import os
from pprint import pprint
from ColorDialog import ColorDialog


class HelpDialog(QtGui.QDialog, ui_Help.Ui_Dialog):
    def __init__(self,mainwindow):
        super(self.__class__, self).__init__()
        #from ui_Help:
        self.updateThemeDelay=100
        self.applyStyleSheetDelay=500
        self.setupUi(self)  
        self.mainwindow=mainwindow
        self.oldbgcol=None

        self.updateStyleSheet()
        self.delayedApplyStyleSheet(delay=self.applyStyleSheetDelay)

        #TAB 5 EDIT CONFIG ##############################################
        configstr=QString("")
        self.helpText.setReadOnly(True)
        self.helpText.appendPlainText(configstr)
        with open(Globals.helptxt) as f:lines=f.read()
        self.helpText.appendPlainText(lines)
        self.helpText.moveCursor(QtGui.QTextCursor.Start)

        self.openSettings.clicked.connect(self.mainwindow.openConfigDialog)
        self.closeHelp.clicked.connect(self.close)


        #myTextEdit -> moveCursor (QTextCursor::Start) ;
#myTextEdit -> ensureCursorVisible() ;

#hier



    def updateStyleSheet(self):
        for i in range(Globals.ncolorstosave):
            n=i+1
            bgcol=Globals.colorshash['bg_color_'+str(n)]

            #b=self.colorButton[i]
            #b.setStyleSheet("""
                 #background-color:{bgcol};
            #""".format(**locals()))
            #b=self.wsColorButton[i]
            #b.setStyleSheet("""
                 #background-color:{bgcol};
            #""".format(**locals()))

        background6=Globals.colorshash['bg_color_6']
        foreground6=Globals.colorshash['fg_color_6']
        background4=Globals.colorshash['bg_color_4']
        foreground4=Globals.colorshash['fg_color_4']
        ts_gen=Globals.colorshash['ts_color_5']
        bs_gen=Globals.colorshash['bs_color_5']
        fg_gen=Globals.colorshash['fg_color_5']
        bg_gen=Globals.colorshash['bg_color_5']
        sel_gen=Globals.colorshash['sel_color_5']
        font=Globals.font
        fontStyle=Globals.fontStyle
        fontSize=Globals.fontSize
        #updated gtk styles dont for some reason take effect for Qt GTK+ style so hmmmf do manually
        #at least for this window
        #how give everything the same color?
        #20221114 fonts erbij gezet
        #added some styles for qt4, because they dont render on qt5 systems
        styles="""
            * {{ 
            background-color:{background6}; color:{foreground6};
            font-family:"{font}"; font-size:{fontSize}px;}}
            }}
            QtGui.QWidget {{ background-color:{background6}; color:{foreground6};}}
            QObject {{ background-color:{background6}; color:{foreground6};}}
            QGridLayout {{ background-color:{background6}; color:{foreground6};}}
            QTabWidget {{ background-color:{background6}; color:{foreground6};}}
            QScrollBar {{ background-color:{background6}; color:{foreground6};}}
            QSlider {{ background-color:{background6}; color:{foreground6};}}
            QWidget {{ background-color:{background6}; color:{foreground6};}}
            QListWidget {{ background-color:{background4}; color:{foreground4};}}
            QListWidgetItem {{ background-color:{background4}; color:{foreground4};}}




            QTabBar::tab {{
                padding: 5px;
                margin: 1px;
                color:			{fg_gen};
                background-color: 	{sel_gen};
                border-style:solid;
                border-width:1px;
                border-top-color:	{ts_gen};
                border-left-color:	{ts_gen};
                border-right-color:	{bs_gen};
                border-bottom-color:	{bs_gen};
             }}

            QTabBar::tab::selected {{
                padding: 5px;
                margin: 1px;
                color:			{fg_gen};
                background-color: 	{bg_gen};
                border-style:solid;
                border-width:1px;
                border-top-color:	{ts_gen};
                border-left-color:	{ts_gen};
                border-right-color:	{bs_gen};
                border-bottom-color:	{bs_gen};
             }}



        """.format(**locals())
        self.setStyleSheet(styles)
        Globals.cdepanel.updateStyleSheet();


    def delayedApplyStyleSheet(self,delay=500):
        #oh damn this is just completely intractable HOW is this supposed to work
        #this all used to work so smoothly when i tried a similar thing 15 years ago ! :'(
        #QtCore.QTimer.singleShot(200,self.applyStyleSheet)
        self.xY5=QtCore.QTimer()
        self.xY5.setSingleShot(True)
        self.xY5.timeout.connect(self.applyStyleSheet)
        self.xY5.start(delay)

    def applyStyleSheet(self):
        def recursive_set(parent):
            for child in parent.findChildren(QtCore.QObject):
            #for child in parent.findChildren(QtGui.QWidget):
                try:
                    child.style().unpolish(self)
                    child.style().polish(self)
                    child.update()
                except: pass
                recursive_set(child)
        recursive_set(self)

def main():

    print 'debugme'


if __name__ == '__main__':           
    main()                          
