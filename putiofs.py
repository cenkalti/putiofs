#!/usr/bin/env python
import argparse
import logging
from errno import ENOENT, EROFS, ENOTSUP, EIO
from stat import S_IFDIR

import putio
from fuse import FUSE, LoggingMixIn, Operations, FuseOSError


class PutioFS(LoggingMixIn, Operations):

    def __init__(self):
        pass

    def access(self, path, amode):
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

        if path != '/':
            raise FuseOSError(ENOENT)
        return dict(st_mode=(S_IFDIR | 0755), st_nlink=2)

    def getxattr(self, path, name, position=0):
        raise FuseOSError(ENOTSUP)

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

        return 0

    def read(self, path, size, offset, fh):
        """Returns a string containing the data requested."""

        raise FuseOSError(EIO)

    def readdir(self, path, fh):
        """
        Can return either a list of names, or a list of (name, attrs, offset)
        tuples. attrs is a dict as in getattr.
        """

        return ['.', '..']

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

        return {}

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='FUSE wrapper for put.io')
    parser.add_argument('mount_point')
    parser.add_argument('oauth_token')
    args = parser.parse_args()
    
    logger = logging.getLogger('putio')
    logging.basicConfig(level=logging.DEBUG)
    
    client = putio.Client(args.oauth_token)
    
    fuse = FUSE(PutioFS(), args.mount_point, foreground=True)
