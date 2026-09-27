#. IMPORTS

# Parse command line args
import argparse

# Read and write config files
import configparser

# for datetime manipulation
from datetime import datetime

# match filenames to support gitignore
from fnmatch import fnmatch

# for reading group/user db because git saves the numerical owner, groupd ID of files
try:
    import grp, pwd
except ModuleNotFoundError:
    pass # These modules are not available on Windows

# Git uses SHA-1 hashing func
import hashlib

# just round up lol
from math import ceil

import os
import re
import sys
import zlib
#. _______________________________________________________

# create an arg parser
argparser = argparse.ArgumentParser(description="The smartest content tracker")

# create subparsers to handle subcommands like init, commit etc. 
# because we dont just call git we call git COMMAND
# dest = "command" means the name of the chosen subparser will be returned as a string
# in a field called command
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True 

# handling our init commands arguments
argsp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")
argsp.add_argument("path",
                   metavar="directory",
                   # 0 or 1 args
                   nargs="?",
                   default=".",
                   help="Where to create the repository.")



"""
Main function calls the bridges functions that represent a specific git command
"""
def main(argv = sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        case "init"         : cmd_init(args)
        case "add"          : cmd_add(args)
        case "status"       : cmd_status(args)
        case "cat-file"     : cmd_cat_file(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "log"          : cmd_log(args)
        case "ls-files"     : cmd_ls_files(args)
        case "checkout"     : cmd_checkout(args)
        case "commit"       : cmd_commit(args)
        case "hash-object"  : cmd_hash_object(args)
        case "ls-tree"      : cmd_ls_tree(args)
        case "rev-parse"    : cmd_rev_parse(args)
        case "rm"           : cmd_rm(args)
        case "show-ref"     : cmd_show_ref(args)
        case "tag"          : cmd_tag(args)
        case _              : print("Bad command.")




class GitRepository(object):
    # abstraction of a git repo

    conf = None
    worktree = None
    gitdir = None

    def __init__(self, path, force= False):
        self.worktree = path 
        self.gitdir = os.path.join(path, ".git")

        if not (os.path.isdir(self.gitdir) or force):
            raise Exception(f"Not a git repo {path}")


        """
        Read config files in .git/config
        """
        self.conf = configparser.ConfigParser()
        confFile = repo_file(self, "config")

        if confFile and os.path.exists(confFile):
            self.conf.read([confFile])
        elif not force:
            raise Exception("Config file is missing")

        if not force :
            vers = int(self.conf.get("core", "repositoryformatversion"))
            # check that core.repositoryformatversion is 0. 
            if vers != 0:
                raise Exception(f"Unsupported repo format version : {vers}")


"""
function variadic, so it can be called with multiple path components as separate arguments. For example, repo_path(repo, "objects", "df", "4ec9fc2ad990cb9da906a95a6eda6627d7b7b0")
"""
def repo_path(repo, *path):
    """Compute path under repo's gitdir."""
    return os.path.join(repo.gitdir, *path)

def repo_file(repo, *path, mkdir=False):
    """Same as repo_path, but create dirname(*path) if absent.  For
    example, repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create
    .git/refs/remotes/origin.
    """
    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)

def repo_dir(repo, *path, mkdir=False):
    """Same as repo_path, but mkdir *path if absent if mkdir."""

    path = repo_path(repo, *path)

    if os.path.exists(path):
        if (os.path.isdir(path)):
            return path
        else:
            raise Exception(f"Not a directory {path}")

    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None



def repo_create(path):
    """Create a new repository at path."""

    repo = GitRepository(path, True)

    # First, we make sure the path either doesn't exist or is an
    # empty dir.

    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception (f"{path} is not a directory!")
        if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
            raise Exception (f"{path} is not empty!")
    else:
        os.makedirs(repo.worktree)

    assert repo_dir(repo, "branches", mkdir=True)
    assert repo_dir(repo, "objects", mkdir=True)
    assert repo_dir(repo, "refs", "tags", mkdir=True)
    assert repo_dir(repo, "refs", "heads", mkdir=True)

    # .git/description
    with open(repo_file(repo, "description"), "w") as f:
        f.write("Unnamed repository; edit this file 'description' to name the repository.\n")

    # .git/HEAD
    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo

def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")

    # version of gitfir format, 0 means initial format, 1 the same wih extensions
    ret.set("core", "repositoryformatversion", "0")

    # disable tracking of file modes (permissions) changes in the work tree
    ret.set("core", "filemode", "false")

    # Indicates that the repo has a workTree
    ret.set("core", "bare", "false")

    return ret



def cmd_init(args):
    repo_create(args.path)