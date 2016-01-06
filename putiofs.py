#!/usr/bin/env python
import argparse
import logging
from time import time
from errno import ENOENT, EROFS, ENOTSUP, EIO, EACCES, EBADF
from stat import S_IFDIR, S_IFREG, S_IRUSR, S_IXUSR
from os import R_OK, W_OK, X_OK, F_OK
import os.path
import calendar
import platform

import putio
from fuse import FUSE, LoggingMixIn, Operations, FuseOSError

now = time()


class PutioFS(LoggingMixIn, Operations):

    def __init__(self):
        self._cache = {}  # path:str -> file:File
        # self.cache["/"] = client.File.get(0)

    def _get_file(self, path):
        """Get file from cache, if not in cache, fetch and fill cache."""

        # OS X makes unnecessary requests to these file names.
        if platform.system() == 'Darwin':
            name = os.path.basename(path).upper()
            if name in ('._.', '.DS_STORE'):
                raise FuseOSError(ENOENT)

        path = path.rstrip('/')
        try:
            return self._cache[path]
        except KeyError:
            if path == '':
                root = client.File.get(0)
                root.path = '/'
                self._cache[path] = root
                return root
            parent_path = os.path.dirname(path)
            parent = self._get_file(parent_path)
            self._cache[parent_path] = parent
            self._get_children(parent)
            try:
                return self._cache[path]
            except KeyError:
                raise FuseOSError(ENOENT)

    def _get_children(self, f):
        try:
            f.children
        except AttributeError:
            f.children = f.dir()
        for child in f.children:
            child.path = os.path.join(f.path, child.name)
            self._cache[child.path] = child
        return f.children

    def access(self, path, amode):
        for name in walk_up(path):
            if amode & (F_OK | R_OK | W_OK | X_OK):
                f = self._get_file(name)
                if amode & W_OK:
                    raise FuseOSError(EACCES)
                if amode & X_OK and f.content_type != 'application/x-directory':
                    raise FuseOSError(EACCES)
        return 0

    bmap = None

    def chmod(self, path, mode):
        raise FuseOSError(EROFS)

    def chown(self, path, uid, gid):
        raise FuseOSError(EROFS)

    def create(self, path, mode, fi=None):
        """
        When raw_fi is False (default case), fi is None and create should
        return a numerical file handle.

        When raw_fi is True the file handle should be set directly by create
        and return 0.
        """

        raise FuseOSError(EROFS)

    def destroy(self, path):
        """Called on filesystem destruction. Path is always /"""

        pass

    def flush(self, path, fh):
        return 0

    def fsync(self, path, datasync, fh):
        return 0

    def fsyncdir(self, path, datasync, fh):
        return 0

    def getattr(self, path, fh=None):
        """
        Returns a dictionary with keys identical to the stat C structure of
        stat(2).

        st_atime, st_mtime and st_ctime should be floats.

        NOTE: There is an incombatibility between Linux and Mac OS X
        concerning st_nlink of directories. Mac OS X counts all files inside
        the directory, while Linux counts only the subdirectories.
        """
        f = self._get_file(path)

        if f.content_type == 'application/x-directory':
            mode = S_IFDIR | S_IRUSR | S_IXUSR
            size = 0
            nlink = 2  # TODO
        else:
            mode = S_IFREG | S_IRUSR
            size = f.size
            nlink = 1

        if f.created_at:
            ctime = calendar.timegm(f.created_at.timetuple())
        else:
            ctime = now

        return dict(st_mode=mode, st_nlink=nlink, st_size=size,
                    st_ctime=ctime, st_mtime=ctime, st_atime=now)

    def init(self, path):
        """
        Called on filesystem initialization. (Path is always /)

        Use it instead of __init__ if you start threads on initialization.
        """

        pass

    def link(self, target, source):
        """creates a hard link `target -> source` (e.g. ln source target)"""

        raise FuseOSError(EROFS)

    def listxattr(self, path):
        return []

    lock = None

    def mkdir(self, path, mode):
        raise FuseOSError(EROFS)

    def mknod(self, path, mode, dev):
        raise FuseOSError(EROFS)

    def open(self, path, flags):
        """
        When raw_fi is False (default case), open should return a numerical
        file handle.

        When raw_fi is True the signature of open becomes:
            open(self, path, fi)

        and the file handle should be set directly.
        """

        return 0

    def opendir(self, path):
        """Returns a numerical file handle."""

        return self._get_file(path).id

    def read(self, path, size, offset, fh):
        """Returns a string containing the data requested."""

        raise FuseOSError(EIO)

    def readdir(self, path, fh):
        """
        Can return either a list of names, or a list of (name, attrs, offset)
        tuples. attrs is a dict as in getattr.
        """

        f = self._get_file(path)
        if fh != f.id:
            raise FuseOSError(EBADF)
        children = self._get_children(f)
        return ['.', '..'] + [c.name for c in children]

    def readlink(self, path):
        raise FuseOSError(ENOENT)

    def release(self, path, fh):
        return 0

    def releasedir(self, path, fh):
        return 0

    def removexattr(self, path, name):
        raise FuseOSError(ENOTSUP)

    def rename(self, old, new):
        raise FuseOSError(EROFS)

    def rmdir(self, path):
        raise FuseOSError(EROFS)

    def setxattr(self, path, name, value, options, position=0):
        raise FuseOSError(ENOTSUP)

    def statfs(self, path):
        """
        Returns a dictionary with keys identical to the statvfs C structure of
        statvfs(3).

        On Mac OS X f_bsize and f_frsize must be a power of 2
        (minimum 512).
        """

        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        """creates a symlink `target -> source` (e.g. ln -s source target)"""

        raise FuseOSError(EROFS)

    def truncate(self, path, length, fh=None):
        raise FuseOSError(EROFS)

    def unlink(self, path):
        raise FuseOSError(EROFS)

    def utimens(self, path, times=None):
        """Times is a (atime, mtime) tuple. If None use current time."""

        return 0

    def write(self, path, data, offset, fh):
        raise FuseOSError(EROFS)


def walk_up(path):
    path = path.rstrip('/')
    while True:
        head, tail = os.path.split(path)
        if tail:
            yield path
        if head == '/':
            yield head
            break
        elif head == '':
            break
        path = head


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='FUSE wrapper for put.io')
    parser.add_argument('mount_point')
    parser.add_argument('oauth_token')
    args = parser.parse_args()
    
    logger = logging.getLogger('putio')
    logging.basicConfig(level=logging.DEBUG)
    
    client = putio.Client(args.oauth_token)
    
    fuse = FUSE(PutioFS(), args.mount_point, foreground=True)
