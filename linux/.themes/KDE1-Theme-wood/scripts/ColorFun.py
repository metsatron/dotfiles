#!/usr/bin/python
#pixmap from text
import cStringIO
from PIL import Image,ImageQt,ImageFilter,ImageEnhance
import os,sys
from PyQt4 import QtGui,QtCore
import re
import subprocess
import Globals
from JosQPainter import JosQPainter
#when switching to some themes, this makes the app crash, so remove
#(someting with py hook something):
#import gtk
#gtk.set_interactive(0)
import threading
import time
from glob import glob

from xdg import IconTheme
from xdg import DesktopEntry

#create text icon the size of baseimage=QPixmap, save to destination file
def textIconSameSizeAsFile(baseimage,destinationfile,text):
    painter = JosQPainter(baseimage)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
    painter.fillRect(0, 0, 1000, 1000, QtCore.Qt.transparent)
    if Globals.smoothTransform:
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform);
    painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
    font=painter.font()
    font.setPointSize (20)
     #//font.setWeight(QtGui.QFont::DemiBold);
    painter.setFont(font)
    painter.setPen(QtGui.QColor('#111111'))
    x=10
    y=22
    painter.drawText(x,y,text)
    painter.setPen(QtCore.Qt.white)
    painter.drawText(x-1,y-1,text)
    painter.end()
    #baseimage.save(destinationfile)#__debug

def convertPixmap(pixmap,brightness,contrast,saturation,sharpness):
    img = QtGui.QImage(pixmap)
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.ReadWrite)
    img.save(buffer, "PNG")
    strio = cStringIO.StringIO()
    strio.write(buffer.data())
    buffer.close()
    strio.seek(0)
    im = Image.open(strio)
    im=ImageEnhance.Brightness(im).enhance(brightness) #default 1
    im=ImageEnhance.Contrast(im).enhance(contrast)
    im=ImageEnhance.Sharpness(im).enhance(sharpness) 
    im=im.filter(ImageFilter.UnsharpMask(radius=0, percent=100, threshold=0)) # default 0 100 0

    converter = ImageEnhance.Color(im)
    im = converter.enhance(saturation)
    #im1.save('/tmp/test.png')

    qt=ImageQt.ImageQt(im)
    imgout=QtGui.QImage(qt)
    rect=imgout.rect()
    #pixmapout=QtGui.QPixmap(imgout) #-> GARBLED IMAGES-----------------------v
    pixmapout=QtGui.QPixmap(imgout.copy(rect)) #Darn.. why. has to do with memory management?
    ################## This also worked: no garbled images when save/load was here:
    #tempfile='/tmp/TempCDEPanelResource'+str(self.tmpfilecounter)+'.png'
    #pixmapout.save(tempfile)
    #pixmapout=QtGui.QPixmap(tempfile)
    return pixmapout

#icon in pixbut is no global resource yet,but file. maybe later
#returns the width
#for drawer entries
def createTextIcon(text,pixelsize,destinationfile,opts=None):
    #font=QtGui.QFont('Lucida Bright') #werkt wel #font.setStyleName('Book') 
    font=QtGui.QFont(Globals.font) #werkt wel
    font.setStyleName(Globals.fontStyle) 
    font.setPixelSize (pixelsize)
    spacing=1
    font.setLetterSpacing(QtGui.QFont.PercentageSpacing,spacing*100)
    fm=QtGui.QFontMetrics(font)
    fm.width(text)
    r=fm.boundingRect(text)
    #hmmm------------------v
    xpm=QtGui.QPixmap(r.width()*1.1,r.height())
    c = QtGui.QColor(0)
    c.setAlpha(0)
    xpm.fill(c)
    #for some reason the string is in the negative half plane so pull it down
    x=-r.x()*spacing*1.1#??
    y=-r.y()
    painter = JosQPainter(xpm)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
    #20221109
    painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform);
    painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
    #toch beter met antialias
    if opts:
        if opts.fontantialias:
            font.setStyleStrategy(QtGui.QFont.PreferAntialias)
        else:
            font.setStyleStrategy(QtGui.QFont.NoAntialias)
    painter.setFont(font)
    painter.setPen(QtGui.QColor('#000000'))
    painter.drawText(x,y,text)
    painter.setPen(QtCore.Qt.white)
    painter.drawText(x-1,y-1,text)
    painter.end()
    if opts:
        xpm=convertPixmap(xpm,1,1,opts.saturation,opts.sharp)
    xpm.save(destinationfile)

    return r.width()




#for workspacebuttons
def drawTextOnPixmap(text,pixelsize,leftmarginfrac,yoffsetfrac,pixmap,opts=None):
    #font=QtGui.QFont('Lucida Bright') #werkt wel
    #font=QtGui.QFont('DejaVu Serif') #werkt wel
    font=QtGui.QFont(Globals.font) #werkt wel
    #font.setStyleName('Book') #doet niks. andere keer uitzoeken
    font.setStyleName(Globals.fontStyle) #doet niks. andere keer uitzoeken
    font.setPixelSize (pixelsize)
    spacing=1
    font.setLetterSpacing(QtGui.QFont.PercentageSpacing,spacing*100)
    #font=QtGui.QFont('Helvetica')
    fm=QtGui.QFontMetrics(font)
    fm.width(text)
    r=fm.boundingRect(text)
    #xpm=QtGui.QPixmap(r.width(),r.height())
    #c = QtGui.QColor(0)
    #c.setAlpha(0)
    #xpm.fill(c)
    #for some reason the string is in the negative half plane so pull it down
    wp=pixmap.size().width()
    hp=pixmap.size().height()
    wt=r.width()
    ht=r.height()
    xt=-r.x()
    yt=-r.y()

    x=xt+leftmarginfrac*wp
    y=yt+(hp-ht)/2+yoffsetfrac*hp

    #dyn=(h-hpn)/2.0+h*yoffsetfrac
    painter = JosQPainter(pixmap)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
    #if Globals.smoothTransform:
    #20221109
    painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform);
    painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
    #BIG NOTE:
        #these antialias etc functions also take into account the font settings
        #in qt5c / fonts.conf of qt. So even if I set 'preferantialias' here
        #then if in fonts.conf is set 'noantialias' , there is NO ANTIALIAS.
        #!!!^#&^@#@#@ WAS ZUM FUCK. 3 HOUERZE LETEEERE
    if opts:
        if opts.fontantialias==0:
            font.setStyleStrategy(QtGui.QFont.NoAntialias)
        else:
            font.setStyleStrategy(QtGui.QFont.PreferAntialias)
    painter.setFont(font)
    painter.setPen(QtGui.QColor('#111111'))
    painter.drawText(x,y,text)
    painter.setPen(QtCore.Qt.white)
    painter.drawText(x-1,y-1,text)
    painter.end()



#take python 
def replaceColors(colors,xpm1):
    rows=len(colors)
    xpm=list(xpm1) #make a copy of the list and make replacements in that, return that
    for row in range(rows):
        colorname=colors[row][0]
        colorval=colors[row][1]
        for j in range(len(xpm)):
            if re.search(colorname,xpm[j]):
                xpm[j]=re.sub('#(?:[0-9a-fA-F]{3}){1,2}',colorval,xpm[j]) #take xpm[j] and replace colorname with colorval and return string
    return xpm


#copy icon to cache dir and (attempt to) cde-ify it. return full path of cached 1996-style icon
# genicon96
#filename has full path
def copyToCacheAndGenCdeIcon(filename,newfilename=None):
        print 'processing icon '+filename
        basename=os.path.basename(filename)
        if newfilename:
            basename=newfilename
        basenamenoext, file_extension = os.path.splitext(basename)
        fullname=os.path.join(Globals.cache,basenamenoext)+'.png'
        #20221114 reworked 1996-style icon generator
        #tried to do everyting in a single convert command using -write mpr:cachfile but that
        #didn't work entirely. so still use a few separate convert commands 
        iconsmall=os.path.join(Globals.tmpdir,'iconsmall.png')
        alpha=os.path.join(Globals.tmpdir,'alpha.png')
        edgebw=os.path.join(Globals.tmpdir,'edgebw.png')

        #/b/iconcdescript
        #alternatieven
        #convert {iconsmall} {edgebw} -composite -ordered-dither o4x4,3 {fullname}
        #convert {iconsmall} {edgebw} -composite -ordered-dither h4x4a,4 {fullname}
        #convert {iconsmall} {edgebw} -composite -dither None -remap /tmp/colortable.gif {fullname}
        #convert {iconsmall} {edgebw} -composite -posterize 4 {fullname}
        #convert {iconsmall} {edgebw} -composite -posterize 5 -ordered-dither o4x4,4 {fullname}
        #convert {iconsmall} {edgebw} -composite -posterize 5 -ordered-dither o8x8,3 {fullname}
        #convert {iconsmall} {edgebw} -composite -posterize 5 -ordered-dither h4x4a,3 {fullname}

        #convert {iconsmall} -posterize 5 -ordered-dither o8x8,3  {iconsmall}

        #OMG SVGS 20221109
        #imagemagic convert doesnt work with pyinstaller due to mixed libraries on
        #different sys.  so first convert to png using qt...  
        #but pixmap doesnt work because not allowed to use outside gui thread (so not in
        #backgroudn icon cache thread)
        #tmppixmap=QtGui.QPixmap(filename)
        #tmppixmap=tmppixmap.scaled(48,48)
        #tmppixmap.save(iconsmall)
        #tmppixmap.save(Globals.tmpdir+'/'+basenamenoext+'.png')

        #this does work for svg conv so first conv to png, and do the rest with convert
        img = QtGui.QImage()
        img.load(filename)
        img.save(iconsmall)
        img.save(Globals.tmpdir+'/'+basenamenoext+'.png')
        #convert {iconsmall} -posterize 8 -dither FloydSteinberg -colors 8  {iconsmall}
        #convert {iconsmall} -posterize 8 -ordered-dither o8x8,3  {iconsmall}
        black='black'
        white='white'

        convertgrey=""
        if Globals.greyicons:
            convertgrey="""convert {fullname} -colorspace Gray {fullname}""".format(**locals()) 

        #sharpen="""  -sharpen 0x1.5""".format(**locals())
        sharpen=""

        #waar komt die 40 vandaan hier
        #zat schaling in josqpainter/drawpixmapcenter
        #here MUST be %, not only a number man--------------------------------V
        #=diepterandjeeen beetje doorzichtig zodat panel kleur wordt
        iconsize=str(Globals.paneliconsize)+'x'+str(Globals.paneliconsize)
        cmd="""
        convert {iconsmall} -resize {iconsize} {sharpen} -channel alpha -threshold 80% -write mpr:out -write {iconsmall} \
        -alpha extract {alpha}
        convert {iconsmall} -posterize 8 -dither FloydSteinberg -colors 8  {iconsmall}
        convert {alpha} -morphology edgeout diamond:1:1 -threshold 90% -write mpr:edge \
        -transparent {black}  -write mpr:edget \
        -channel RGB -negate -write mpr:edgetn \
        -sparse-color voronoi "%[fx:(w-h)/2],%[fx:(h-w)/2] {black} %[fx:(w+h)/2],%[fx:(h+w)/2] {white}" mpr:edgen mpr:edgetn -reverse -composite -fill '#ffffff' -opaque white -fill '#222222' -opaque black {edgebw}
        convert {edgebw} -alpha set -background none -channel A -evaluate multiply 0.65 +channel {iconsmall} -composite  -auto-level -gamma 1.1 -brightness-contrast 0x10 {fullname}
        {convertgrey}
        """.format(**locals())
        #---------------------------------------------------------------------------A doorz van rand

        #print 'cmd '+str(cmd)#__debug
        out = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (stdout, stderr) = out.communicate()
        print stdout
        print stderr

        ###########################
        #__debug image process
        #buf=Globals.tmpdir+'/out.png'
        #cmd="""cp {fullname} {buf}""".format(**locals())
        #os.system(cmd)
        #if basenamenoext=="edit-find":
            #sys.exit()
        ###########################

        return fullname

def copyToCache(filename,newfilename=None):
        basename=os.path.basename(filename)
        if newfilename:
            basename=newfilename
        basenamenoext, file_extension = os.path.splitext(basename)
        fullname=os.path.join(Globals.cache,basenamenoext)+'.png'
        cmd=("""cp {filename} {fullname} """.format(**locals()))
        out = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (stdout, stderr) = out.communicate()



#xpm / png dond treally need separate cmd call todo. later.. later..
def findIconFromName1(name):
    print '\n Looking for icon:'+name+'...'
    def err(name):
        print """ICON NOT FOUND {name} PLEASE CHECK. USING DEFAULT ICON """.format(**locals())

    #IF NO ICON GIVEN OR WHATEVER, RETURN DEFAULT ICON
    if name=='' or name==None: 
        err(name)
        return Globals.defaultxpm

    #search icons here. #Globals.xpmdir only for system xpms like exit button.  #/usr/local also later
    #glob subdirectories of /usr/share/icons
    sysicondirs=glob('/usr/share/icons/*/')
    #remove ugly ones
    sysicondirs = [x for x in sysicondirs if not re.search(r'HighContrast', x)]
    #search these first
    icondirsfirst=[Globals.xpmdir, '/usr/share/icons/NsCDE',  '/usr/share/icons/elementary-xfce','/usr/share/icons/gnome'] 
    #icondirsfirst=[] 
    #hmmon debian stable HighContrast is about the only one available. Do this better
    icondirs=icondirsfirst+sysicondirs+['/usr/share/icons/HighContrast']
    pixmapdir='/usr/share/pixmaps'


    extensions=['png','xpm','svg'] 

    #20221106 now icons are sometimes listed as Icon=org.xfce.terminal 
    #without extension, but with dots! so only remove image extensions
    basenameext=os.path.basename(name)
    basename=re.sub(".png|.xpm|.svg|.jpg|.PNG|.XPM|.SVG|.JPG", "", basenameext)

    #check if basename.png is in cache (if not all icons will be put there as png later)
    cachedicon=os.path.join(Globals.cache,basename+'.png')
    if os.path.isfile(cachedicon):
        print 'Icon found in cache '+cachedicon
        return cachedicon

    #ICON WITH A FULL PATH GIVEN  (because somtimes the icon is not in /usr/share/icons)
    if not os.path.basename(name)==name: #has full path-check
        if os.path.isfile(name): 
            print 'Icon with full path found, copying to cache'+name
            cachediconwithpath=copyToCacheAndGenCdeIcon(name)
            return cachediconwithpath
        else: 
            #misschien gewoon doorgaan
            err(name)
            return Globals.defaultxpm

    print 'SEARCHING FOR ICON '+name

    #ICON NAME WITHOUT PATH GIVEN
    #in case given without extension: search for basename*, with ext: basenameext* also ok
    #but in the first case, basenameext=basename so search for basenameext* in both cases



    #more extensive search and copy to cache if found #always QUOTE globs in 'find' statements WHY #in som icon dirs it is not
    #48x48 so grep only 48 #20221108 moet zijn eerst basename, dan evt die naar cache copieren anders basename * voor alternatief
    #maar dan basenamen aar cache clop
    print 'MORE EXTENSIVE SEARCH...'
    print 'looking for icon in system icon dirs...'
    for b in icondirs:
        #hier uitgaan van een grotere levert een beter resultaat voor kleine icon na omlaag schalen
        #cmd=("""find {b} -name "{basenameext}*" -print|grep -E '64|72|96|128|256|scalable'""".format(**locals()))
        cmd=("""find {b} -name "{basenameext}*" -print|grep -E '96|128|256|scalable'""".format(**locals()))
        out = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (stdout, stderr) = out.communicate()
        if stdout:
            l=stdout.splitlines()
            c=Globals.cache
            print 'found icon  '+l[0]
            cachediconwithpath=copyToCacheAndGenCdeIcon(l[0],basename+'.png')
            return cachediconwithpath
        #put in on efunc, larger ones first
    print 'Trying smaller one...'
    for b in icondirs:
        cmd=("""find {b} -name "{basenameext}*" -print|grep -E '48|64'""".format(**locals()))
        out = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (stdout, stderr) = out.communicate()
        if stdout:
            l=stdout.splitlines()
            c=Globals.cache
            print 'found icon  '+l[0]
            cachediconwithpath=copyToCacheAndGenCdeIcon(l[0],basename+'.png')
            return cachediconwithpath
    print 'nope...'
    print 'looking in pixmap dir'
    cmd=("""find {pixmapdir} -name "{basenameext}*" -print""".format(**locals()))
    out = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (stdout, stderr) = out.communicate()
    if stdout:
        l=stdout.splitlines()
        c=Globals.cache
        print 'found icon  '+l[0]
        cachediconwithpath=copyToCacheAndGenCdeIcon(l[0],basename+'.png')
        return cachediconwithpath

    #search everything. maybe step through result with 'identify' later
    print 'NOTHING... search the entire system now using locate...'
    if which('locate'):
        for e in extensions: #here we need grep of extensions, because non img results are also in the 'locate' 
            cmd=("""locate {basenameext}|grep icon|grep -i {e}""".format(**locals()))
            out = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            (stdout, stderr) = out.communicate()
            if stdout:
                l=stdout.splitlines()
                c=Globals.cache
                ####this search original eg 'xterm' couldnt be found, so maybe chooses 'xterm-color.png'
                ####so for quick, make copy of that with name xterm in cache
                ####or make cache 'xterm_alt.png' and then check next time also for filname'_alt' or something
                ####.... later later leave for now 
                ####BUT then create 'xterm' to cache directory, not 'xterm-color', otherwise it will next
                ####time also not find it...
                print """ICON {name} NOT FOUND SO USING ALTERNATIVE {l[0]} INSTEAD. PLS CHECK """.format(**locals())
                cachediconwithpath=copyToCacheAndGenCdeIcon(l[0],basename+'.png')
                return cachediconwithpath

    #finally, give up
    err(name)
    cachediconwithpath=copyToCacheAndGenCdeIcon(Globals.defaultxpm,basename+'.png')
    return cachediconwithpath

def which(program):
    path_ext = [""];
    ext_list = None

    if sys.platform == "win32":
        ext_list = [ext.lower() for ext in os.environ["PATHEXT"].split(";")]

    def is_exe(fpath):
        exe = os.path.isfile(fpath) and os.access(fpath, os.X_OK)
        # search for executable under windows
        if not exe:
            if ext_list:
                for ext in ext_list:
                    exe_path = "%s%s" % (fpath,ext)
                    if os.path.isfile(exe_path) and os.access(exe_path, os.X_OK):
                        path_ext[0] = ext
                        return True
                return False
        return exe

    fpath, fname = os.path.split(program)

    if fpath:
        if is_exe(program):
            return "%s%s" % (program, path_ext[0])
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return "%s%s" % (exe_file, path_ext[0])
    return None


    #def function_that_downloads(my_args):
    #import threading
    #def my_inline_function(some_args):
        # do some stuff
        #download_thread = threading.Thread(target=function_that_downloads, name="Downloader", args=some_args)
        #download_thread.start()

# cde-ize and cache drawer icons in advance
# called in separate thread from main program
def cacheIcons():

    #wait a bit
    print 'CACHING ICONS...'
    print 'CACHING ICONS...'
    print 'CACHING ICONS...'
    print 'CACHING ICONS...'
    print 'CACHING ICONS...'
    print 'CACHING ICONS...'
    print 'CACHING ICONS...'

    drawerdir=Globals.drawerdir
    print drawerdir
    cmd="""
    grep desktop {drawerdir}/*
    """.format(**locals())
    out = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (stdout, stderr) = out.communicate()

    for desktopfile in stdout.splitlines():
        desktopfile=re.sub('^.*:',"",desktopfile)
        d=DesktopEntry.DesktopEntry(desktopfile)
        iconnamenoext=d.getIcon()
        print '\n\nFind icon for combobutton '+iconnamenoext
        icon=findIconFromName1(iconnamenoext)

    return None



if __name__ == '__main__':

    #8 or reduced 4 color palette
    #colors=readMotifColors('4','Broica.dp')
    #colors=readMotifColors('8','Broica.dp')


    #xpm=extractXpm('xpm/launcher.xpm')
    #xpm1=replaceColors(colors,xpm)

    #app = QtCore.QApplication(sys.argv)
    #window = QtGui.QMainWindow()

    #pic = QtGui.QLabel(window)

    #########################
    #pixmap=QtGui.QPixmap(xpm) #the original one
    #pixmap=QtGui.QPixmap(xpm1) #the replaced one
    #########################

    #pic.setPixmap(pixmap)
    #pic.resize(200,100)

    #for testing
    Globals.cache='/x/pycde/scaletest/cdepanel/cache'
    Globals.defaultxpm='/x/pycde/scaletest/cdepanel/xpm/empty.xpm'
    Globals.xpmdir='/x/pycde/scaletest/cdepanel/xpm'

    ##################################################
    #print findIconFromName1('mozilla.xpm')
    #print findIconFromName1('xterm')
    #print findIconFromName1('firefox.png')
    #print findIconFromName1('org.xfce.terminal')
    #print findIconFromName1('')
    #print findIconFromName1(None)
    #print findIconFromName1('/x/pycde/scaletest/cdepanel/xpm/terminal.xpm')
    #print findIconFromName1('/x/ycde/scaletest/cdepanel/xpm/txxxxeminal.xpm')

    ##################################################
    #app = QtCore.QApplication(sys.argv)
    #p=QtGui.QPixmap('xpm/pager-button-1.xpm')
    #textIconSameSizeAsFile(p,'/tmp/testicon.png','My Text')
    #print 'done'
    #sys.exit(app.exec_())
    ##################################################






    app = QtCore.QApplication(sys.argv)

    ###########################3
    #print createTextIcon('/tmp/testicon.png','M111yTExxxxxxxxxxxxxxxXT 123')
    print 'done'

    ###########################3
    #pixmap=QtGui.QPixmap('/tmp/testpagerbutton2.png')
    #drawTextOnPixmap('Hello',14,.1,0.05,pixmap)
    #pixmap.save('/tmp/1.png')
    
    sys.exit()

    sys.exit(app.exec_())


    #window.show()
    #sys.exit(app.exec_())
