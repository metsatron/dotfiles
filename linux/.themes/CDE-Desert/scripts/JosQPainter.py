#!/usr/bin/python
#CUSTOM PAINTER CLASS WITH CENTER PIXMAP 
#zie PicButton.py
#import signal
#signal.signal(signal.SIGINT, signal.SIG_DFL)
#import sys
from PyQt4 import QtCore, QtGui

class JosQPainter (QtGui.QPainter):
   def __init__(self, parent=None):
      super(JosQPainter, self).__init__(parent)
   def drawPixmapCenter(self, rect, iconsizefac, pixmap):
        w=rect.width()
        h=rect.height()
	wp=pixmap.size().width()
	hp=pixmap.size().height()
        #waarom:
        if hp==0:
            return
        #choose iconsizefac such that for non scaled panel height, the icon 
        #is also not scaled and displayed at its own size. Then no softening 
        #but crisp pixels
	hpn=h*iconsizefac#new h for the pixmap, frac portion of rect height
	wpn=float(wp)/hp*hpn #new w for pixmap perserve aspect
	dxn=(w-wpn)/2.0 #offsets for centering
	dyn=(h-hpn)/2.0
	QtGui.QPainter.drawPixmap(self,dxn,dyn,wpn,hpn, pixmap)
   def drawPixmapLeft(self, rect, leftmarginfrac, heightfrac, yoffsetfrac, pixmap):
        w=rect.width()
        h=rect.height()
	wp=pixmap.size().width()
	hp=pixmap.size().height()
        if hp==0:
            return
	hpn=h*heightfrac #new h for the pixmap, frac portion of rect height
	wpn=float(wp)/hp*hpn #new w for pixmap perserve aspect
	#dxn=(w-wpn)/2.0 #offsets for centering
        dxn=float(w)*leftmarginfrac
	#dxn=100
	dyn=(h-hpn)/2.0+h*yoffsetfrac
	QtGui.QPainter.drawPixmap(self,dxn,dyn,wpn,hpn, pixmap)

#MAKE TEST WIDGET WHEN THIS FILE IS RUN AS PROGRAM
class Test (QtGui.QWidget):
    def __init__(self):
        super(Test, self).__init__()
        self.initUI()
    def initUI(self):
        self.show()
    def paintEvent(self, event):
        painter = JosQPainter(self)
        #painter.drawPixmapCenter(event.rect(), QtGui.QPixmap("terminal.xpm"))
        #painter.drawPixmapCenter(event.rect(), QtGui.QPixmap("createdIcon.png"))
#hier

def main():
   app = QtCore.QApplication(sys.argv)
   test = Test()
   test.show()
   test.resize(100,100)
   sys.exit(app.exec_())
	
if __name__ == '__main__':
   main()
