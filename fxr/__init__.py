#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# module: fxr
# author: Panagiotis Mavrogiorgos - pmav99 google mail

"""

    python3 fxr single 'search_pattern' 'replace' /path/to/file

    python3 fxr multi 'search_pattern' 'replace' -s -l --hidden

"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import re
import sys
import shutil
import argparse
import subprocess


from contextlib import contextmanager
import io
import os



@contextmanager
def inplace(filename, mode='r', buffering=-1, encoding=None, errors=None,
            newline=None, backup_extension=None):
    """Allow for a file to be replaced with new content.

    yields a tuple of (readable, writable) file objects, where writable
    replaces readable.

    If an exception occurs, the old file is restored, removing the
    written data.

    mode should *not* use 'w', 'a' or '+'; only read-only-modes are supported.

    http://www.zopatista.com/python/2013/11/26/inplace-file-rewriting/

    """

    # move existing file to backup, create new file with same permissions
    # borrowed extensively from the fileinput module
    if set(mode).intersection('wa+'):
        raise ValueError('Only read-only file modes can be used')

    backupfilename = filename + (backup_extension or os.extsep + 'bak')
    try:
        os.unlink(backupfilename)
    except os.error:
        pass
    os.rename(filename, backupfilename)
    readable = io.open(backupfilename, mode, buffering=buffering,
                       encoding=encoding, errors=errors, newline=newline)
    try:
        perm = os.fstat(readable.fileno()).st_mode
    except OSError:
        writable = open(filename, 'w' + mode.replace('r', ''),
                        buffering=buffering, encoding=encoding, errors=errors,
                        newline=newline)
    else:
        os_mode = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
        if hasattr(os, 'O_BINARY'):
            os_mode |= os.O_BINARY
        fd = os.open(filename, os_mode, perm)
        writable = io.open(fd, "w" + mode.replace('r', ''), buffering=buffering,
                           encoding=encoding, errors=errors, newline=newline)
        try:
            if hasattr(os, 'chmod'):
                os.chmod(filename, perm)
        except OSError:
            pass
    try:
        yield readable, writable
    except Exception:
        # move backup back
        os.replace(backupfilename, filename)
        raise
        # try:
            # os.unlink(filename)
        # except os.error:
            # pass
        # os.rename(backupfilename, filename)
        # raise
    finally:
        readable.close()
        writable.close()
        try:
            os.unlink(backupfilename)
        except os.error:
            pass


def literal_replace(pattern, replacement, original):
    return original.replace(pattern, replacement)


def regex_replace(pattern, replacement, original):
    return re.sub(pattern, replacement, original)


def apply_search_and_replace(pattern, replacement, filepath, literal, raise_on_error=False):
    # open file
    with open(filepath) as fd:
        original = fd.read()
    # replace text
    replace_method = literal_replace if literal else regex_replace
    substituted = replace_method(pattern, replacement, original)
    if original == substituted:
        msg = "no substitutions made: %s" % filepath
        if raise_on_error:
            sys.exit(msg)
        else:
            print("Warning: %s" % msg)
    else:
        # write file inplace
        with open(filepath, "w") as fd:
            fd.write(substituted)


def search_for_files(search_prog, search_args, pattern):
    # Check if the search engine is available
    if shutil.which(search_prog) is None:
        sys.exit("Coulnd't find <%s>. Please install it and try again." % search_prog)
    # We DO need "-l" when we use ag!
    if search_prog == "ag":
        if search_args and "-l" not in search_args:
            search_args.append("-l")
        else:
            search_args = ['-l']
    cmd = [search_prog]
    cmd.extend(search_args)
    cmd.append(pattern)
    try:
        output = subprocess.check_output(cmd)
        filepaths = output.decode("utf-8").splitlines()
    except subprocess.CalledProcessError:
        sys.exit("Couldn't find any matches. Check your the pattern: %s" % pattern)
    return filepaths


def main(args):
    filepaths = [args.filepath] if args.mode == "single" else search_for_files(args.search_prog, args.search_args, args.pattern)
    raise_on_error = (len(filepaths) == 1)
    for filepath in filepaths:
        apply_search_and_replace(args.pattern, args.replacement, filepath, args.literal, raise_on_error)


def add_text(args, filepath, raise_on_error=True, **kwargs):
    # input validation
    if args.pattern == '' or args.added_text == '':
        sys.exit("In <add> mode, you must specify both <pattern> and <added_text>.")
    added_text = args.added_text + "\n"
    prepend = args.prepend
    pattern = re.compile(args.pattern)
    found = False
    with inplace(filepath, "r") as (infile, outfile):
        for line in infile:
            if pattern.search(line):
                found = True
                lines = [added_text, line] if prepend else [line, added_text]
                outfile.writelines(lines)
            else:
                outfile.write(line)
    if not found:
        msg = "Couldn't find a match."
        if raise_on_error:
            raise sys.exit(msg)
        else:
            print(msg)


DISPATCHER = {
    "add": add_text,
}


def main(args):
    run = DISPATCHER[args.mode]
    if args.single:
        filepaths = [args.single]
    else:
        filepaths = search_for_files(args.search_prog, args.search_args, args.pattern)
    for filepath in filepaths:
        run(args, filepath)


def cli():
    # create the top-level parser
    main_parser = argparse.ArgumentParser(description="A pure python 'search & replace' script.")
    # Create the parent-parser which contains the common options among the subparsers.
    # parent_parser = argparse.ArgumentParser(add_help=False)
    # parent_parser.add_argument("pattern", help="The regex pattern we want to match.")
    # parent_parser.add_argument("replacement", help="The text we want to replace <pattern> with.")
    # parent_parser.add_argument("--debug", action="store_true", default=False, help="Debug mode on")
    # parent_parser.add_argument("--literal", action="store_true", default=False, help="Make a literal substitution (i.e. don't treat <pattern> as a regex).")

    ### Create the sub-parsers.
    subparsers = main_parser.add_subparsers(help='Choose mode of operation', dest='mode', title="subcommands", description="Valid subcommands")
    add_parser = subparsers.add_parser("add", help="Search for files containing <pattern> and add text before or after the matches.")
    delete_parser = subparsers.add_parser("delete", help="Delete text lines before or after match.")
    replace_parser = subparsers.add_parser("replace", help="Replace text.")

    ### Add
    add_parser.add_argument("pattern", help="The regex pattern we want to match.")
    add_parser.add_argument("added_text", help="The text that we want to add.")
    add_parser.add_argument("--single", action="store", default=False, help="Add text only to the specified file.")
    add_parser.add_argument("--prepend", action="store_true", help="Prepend text to the <pattern>'s matches. Defaults to False.")
    add_parser.add_argument("--literal", action="store_true", default=False,
                            help="Search literally for <pattern>, i.e. don't treat <pattern> as a regex.")
    add_parser.add_argument("--search-prog", help="The executable that we want to use in order to search for matches. Defaults to 'ag'.", default="ag -s -l --hidden", metavar='')
    # add_parser.add_argument("search_args", help="Any added_textal arguments are passed to the search executable (i.e. 'ag').", nargs=argparse.REMAINDER, default=('-s', '-l', '--hidden'))

    ### Delete
    # delete_parser.add_argument("pattern", help="The regex pattern we want to match.")


    ### Replace
    # replace_parser.add_argument("pattern", help="The regex pattern we want to match.")

    # single_parser = subparsers.add_parser('single', help='"Search & replace" on a single file', parents=[parent_parser])
    # multi_parser = subparsers.add_parser('multi', help='Search for files matching pattern and replace all occurrences.', parents=[parent_parser], add_help=True)
    # append_parser = subparsers.add_parser('append', help='Search for files matching pattern and append lines before of after each match.', parents=[parent_parser], add_help=True)
    # delete_parser = subparsers.add_parser('delete', help='Search for files matching pattern and append lines before of after each match.', parents=[parent_parser], add_help=True)
    # # single parser arguments
    # single_parser.add_argument("filepath", help="The path to the file on which we want to replace text.")
    # # multi parser arguments
    # multi_parser.add_argument("search_args", help="Any added_textal arguments are passed to the search executable (i.e. 'ag').", nargs=argparse.REMAINDER, default=('-s', '-l', '--hidden'))
    # multi_parser.add_argument("--search-prog", help="The executable that we want to use in order to search for matches. Defaults to 'ag'.", default="ag", metavar='')
    args = main_parser.parse_args()
    # if args.debug:
        # print(args)
    if args.mode:
        main(args)
    else:
        main_parser.print_help()
        sys.exit(0)
