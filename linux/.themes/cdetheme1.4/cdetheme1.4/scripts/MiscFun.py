#!/usr/bin/python
#import signal
#signal.signal(signal.SIGINT, signal.SIG_DFL)
import os.path
import subprocess
import sys
import os



#calling xfconf-query (or other external commands) from inside pyinstaller environemnt
#can cause problems: remove LD_LIBRARY_PATH from env if present (this is inside pyinstaller env)
pip_env = os.environ.copy()
if 'LD_LIBRARY_PATH' in pip_env:
    pip_env.pop('LD_LIBRARY_PATH')


def cmd_exists(cmd, path=None):
    """ test if path contains an executable file with name
    """
    if path is None:
        path = os.environ["PATH"].split(os.pathsep)

    for prefix in path:
        filename = os.path.join(prefix, cmd)
        executable = os.access(filename, os.X_OK)
        is_not_directory = os.path.isfile(filename)
        if executable and is_not_directory:
            return True
    return False

def execWithShell1(cmd):
    #calling xfconf-query (or other external commands) from inside pyinstaller environemnt
    #can cause problems: remove LD_LIBRARY_PATH from env if present (this is inside pyinstaller env)
    pip_env = os.environ.copy()
    if 'LD_LIBRARY_PATH' in pip_env:
        pip_env.pop('LD_LIBRARY_PATH')
    print cmd
    #cmd='echo hello'
    print subprocess.check_output(cmd, shell=True, env=pip_env)

#this also seems to introduce quite a delay
def execWithShell(cmd):
    pip_env = os.environ.copy()
    if 'LD_LIBRARY_PATH' in pip_env:
        pip_env.pop('LD_LIBRARY_PATH')
    try:
        output=subprocess.check_output(cmd, shell=True, env=pip_env)
    except subprocess.CalledProcessError as e:
        print cmd
        print '!!!!!!!!!!!!!!!!!!!subprocess ERROR!!!!!!!!!!!!!!!!!!!!!!!'
        print e.output
        output=''
    return output
def execWithShellThread(cmd):
        #print os.environ['PATH']
        pip_env = os.environ.copy()
        if 'LD_LIBRARY_PATH' in pip_env:
            pip_env.pop('LD_LIBRARY_PATH')
        try: 
            p=subprocess.Popen(cmd,shell=True, env=pip_env) 
        except OSError as e: 
            #this doesnt seem to work
            print cmd
            print '!!!!!!!!!!!!!!!!!!!subprocess ERROR!!!!!!!!!!!!!!!!!!!!!!!'
            print e.output
            p=''
        return p
def checkFile(filename):
    if os.path.isfile(filename):
        return filename
    else:
        print 'FILE NOT FOUND: '+filename
        sys.exit()
def checkDir(filename):
    if os.path.isdir(filename):
        return filename
    else:
        print 'DIRECTORY NOT FOUND: '+filename
        sys.exit()

