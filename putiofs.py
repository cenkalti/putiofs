#!/usr/bin/env python

import os
import logging
import argparse

from errno import ENOENT, EROFS
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time
from tempfile import NamedTemporaryFile
from pdb import set_trace as st

import putio2
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

now = time()

class PutioFS(LoggingMixIn, Operations):
    """Implementation of put.io filesystem"""
    
    def __init__(self):
        self.fd = 0
        self.temporary_files = {} # buffer area before uploading {path: TemporaryFile}
        self._fetch_files()
    
    def _fetch_files(self):
        '''Fetch all files from put.io''' 
        
        # -1 means all files
        self.files = client.File.list(-1, as_dict=True)
        # as {id: file}
        
        # create root
        self.files[0] = client.File(dict(id=0, name='Your Files',
            content_type='application/x-directory',
            parent_id=None))
        
        # attact stat object to files
        for f in self.files.values():
            self._attach_stat(f)
        
        # same files by indexed with path
        self.path_files = {}
        for f in self.files.values():
            path = self._construct_path(f)
            self.path_files[path] = f
    
    def _add_to_files(self, file):
        self.files[file.id] = file
        path = self._construct_path(file)
        self.path_files[path] = file
        self._attach_stat(file)
    
    def _attach_stat(self, file):
        if file.content_type == 'application/x-directory':
            mode = (S_IFDIR | 0700)
            size = 0
        else:
            mode = (S_IFREG | 0400)
            size = file.size
            
        file.stat = dict(
            st_mode=mode,
            st_ctime=now,
            st_atime=now,
            st_size=size,
            st_blksize=1000000
            # st_blksize a filesystem-specific preferred I/O block size for this object.
            # but, nobody seems to respect it.
        )
            
    def _construct_path(self, file):
        '''For given file, returns the path to the mount point'''
        
        if file.id == 0:
            return '/'
        
        path = str(file)

        parent_id = file.parent_id
        while parent_id:
            parent = self.files[parent_id]
            path = str(parent) + '/' + path

            parent_id = parent.parent_id

        return '/' + path
        
    def _get_file_by_path(self, path):
        return self.path_files[path]
    
    def _get_file_by_id(self, id):
        return self.files[id]
    
    def _children(self, file):
        return filter(lambda f: f.parent_id == file.id, self.files.values())
         
    def create(self, path, mode):
        if path in self.temporary_files:
            raise FuseOSError(EROFS)
        
        self.temporary_files[path] = NamedTemporaryFile(delete=False)

        self.fd += 1
        return self.fd
    
    def getattr(self, path, fh=None):
        try:
            f = self.temporary_files[path]
        except KeyError:
            pass
        else:
            st = os.lstat(f.name)
            return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
            
        if path not in self.path_files:
            raise FuseOSError(ENOENT)
            
        file = self._get_file_by_path(path)
        return file.stat
    
    # def mkdir(self, path, mode):
    #         self.files[path] = dict(st_mode=(S_IFDIR | mode), st_nlink=2,
    #                 st_size=0, st_ctime=time(), st_mtime=time(), st_atime=time())
    #         self.files['/']['st_nlink'] += 1

    def open(self, path, flags):
        self.fd += 1
        return self.fd
    
    def read(self, path, size, offset, fh):
        f = self._get_file_by_path(path)
        return f.download(range=(offset, offset+size))
    
    def readdir(self, path, fh):
        f = self._get_file_by_path(path)
        children = self._children(f)
        return ['.', '..'] + [str(c) for c in children]
    
    def release(self, path, fh):
        try:
            f = self.temporary_files[path]
        except KeyError:
            # no need to close files which are opened for reading
            pass
        else:
            temppath = f.name
            f.close()
        
            try:
                filename = os.path.basename(path)
                newfile = client.File.upload(temppath, filename)
                self._add_to_files(newfile)
            finally:
                os.remove(temppath)
                del self.temporary_files[path]

    # def rename(self, old, new):
    #         self.files[new] = self.files.pop(old)
    #     
    #     def rmdir(self, path):
    #         self.files.pop(path)
    #         self.files['/']['st_nlink'] -= 1
    
    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)
    
    def write(self, path, data, offset, fh):
        f = self.temporary_files[path]
        f.seek(offset)
        f.write(data)
        return len(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='FUSE wrapper for put.io')
    parser.add_argument('mount_point')
    parser.add_argument('oauth_token')
    args = parser.parse_args()
    
    logger = logging.getLogger('putio2')
    logging.basicConfig(level=logging.DEBUG)
    
    client = putio2.Client(args.oauth_token)
    
    fuse = FUSE(PutioFS(), args.mount_point, foreground=True)
