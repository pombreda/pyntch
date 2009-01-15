#!/usr/bin/env python
# module: 'posix'

EX_CANTCREAT = 0
EX_CONFIG = 0
EX_DATAERR = 0
EX_IOERR = 0
EX_NOHOST = 0
EX_NOINPUT = 0
EX_NOPERM = 0
EX_NOUSER = 0
EX_OK = 0
EX_OSERR = 0
EX_OSFILE = 0
EX_PROTOCOL = 0
EX_SOFTWARE = 0
EX_TEMPFAIL = 0
EX_UNAVAILABLE = 0
EX_USAGE = 0
F_OK = 0
NGROUPS_MAX = 0
O_APPEND = 0
O_CREAT = 0
O_DIRECT = 0
O_DIRECTORY = 0
O_DSYNC = 0
O_EXCL = 0
O_LARGEFILE = 0
O_NDELAY = 0
O_NOCTTY = 0
O_NOFOLLOW = 0
O_NONBLOCK = 0
O_RDONLY = 0
O_RDWR = 0
O_RSYNC = 0
O_SYNC = 0
O_TRUNC = 0
O_WRONLY = 0
R_OK = 0
TMP_MAX = 0
WCONTINUED = 0
WNOHANG = 0
WUNTRACED = 0
W_OK = 0
X_OK = 0

class error(object): pass
class stat_result(object): pass
class statvfs_result(object): pass

pathconf_names = {'': 0}
sysconf_names = {'': 0}
confstr_names = {'': 0}
environ = {'': ''}

def WCOREDUMP(x):
  assert isinstance(x, int)
  return False
def WEXITSTATUS(x):
  assert isinstance(x, int)
  return 0
def WIFCONTINUED(x):
  assert isinstance(x, int)
  return False
def WIFEXITED(x):
  assert isinstance(x, int)
  return False
def WIFSIGNALED(x):
  assert isinstance(x, int)
  return False
def WIFSTOPPED(x):
  assert isinstance(x, int)
  return False
def WSTOPSIG(x): 
  assert isinstance(x, int)
  return 0
def WTERMSIG(x):
  assert isinstance(x, int)
  return 0

def _exit(x):
  assert isinstance(x, int)

def abort(): return

def access(path, mode):
  assert isinstance(path, str)
  assert isinstance(mode, int)
  return
def chdir(path):
  assert isinstance(path, str)
  return
def chmod(path, mode):
  assert isinstance(path, str)
  assert isinstance(mode, int)
  return
def chown(path, uid, gid):
  assert isinstance(path, str)
  assert isinstance(uid, int)
  assert isinstance(gid, int)
  return
def chroot(path):
  assert isinstance(path, str)
  return
def close(fd):
  assert isinstance(fd, int)
  return
def confstr(x): return ''
def ctermid(): return ''
def dup(fd):
  assert isinstance(fd, int)
  return 0
def dup2(fd1,fd2):
  assert isinstance(fd1, int)
  assert isinstance(fd2, int)
  return

def execv(*x): return

def execve(*x): return

def fchdir(*x): return

def fdatasync(*x): return

def fdopen(*x): return

def fork(*x): return

def forkpty(*x): return

def fpathconf(*x): return

def fstat(*x): return

def fstatvfs(*x): return

def fsync(*x): return

def ftruncate(*x): return

def getcwd(*x): return

def getcwdu(*x): return

def getegid(*x): return

def geteuid(*x): return

def getgid(*x): return

def getgroups(*x): return

def getloadavg(*x): return

def getlogin(*x): return

def getpgid(*x): return

def getpgrp(*x): return

def getpid(*x): return

def getppid(*x): return

def getsid(*x): return

def getuid(*x): return

def isatty(*x): return

def kill(*x): return

def killpg(*x): return

def lchown(*x): return

def link(*x): return

def listdir(*x): return

def lseek(*x): return

def lstat(*x): return

def major(*x): return

def makedev(*x): return

def minor(*x): return

def mkdir(*x): return

def mkfifo(*x): return

def mknod(*x): return

def nice(*x): return

def open(*x): return

def openpty(*x): return

def pathconf(*x): return

def pipe(*x): return

def popen(*x): return

def putenv(*x): return

def read(*x): return

def readlink(*x): return

def remove(*x): return

def rename(*x): return

def rmdir(*x): return

def setegid(*x): return

def seteuid(*x): return

def setgid(*x): return

def setgroups(*x): return

def setpgid(*x): return

def setpgrp(*x): return

def setregid(*x): return

def setreuid(*x): return

def setsid(*x): return

def setuid(*x): return

def stat(*x): return

def stat_float_times(*x): return

def statvfs(*x): return

def strerror(*x): return

def symlink(*x): return

def sysconf(*x): return

def system(*x): return

def tcgetpgrp(*x): return

def tcsetpgrp(*x): return

def tempnam(*x): return

def times(*x): return

def tmpfile(*x): return

def tmpnam(*x): return

def ttyname(*x): return

def umask(*x): return

def uname(*x): return

def unlink(*x): return

def unsetenv(*x): return

def utime(*x): return

def wait(*x): return

def wait3(*x): return

def wait4(*x): return

def waitpid(*x): return

def write(*x): return

