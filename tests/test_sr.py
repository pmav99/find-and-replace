#!/usr/bin/env python
# -*- coding: utf-8 -*-
# module:
# author: Panagiotis Mavrogiorgos <pmav99,gmail>

"""

"""

import shlex
import subprocess

import pytest


@pytest.fixture
def temp_file(tmpdir):
    sample_file = tmpdir.join("file.txt")
    return sample_file


def run_single(pattern, replacement, filepath):
    cmd = "python3 sr.py single '{pattern}' '{replacement}' {filepath} "
    cmd = shlex.split(cmd.format(pattern=pattern, replacement=replacement, filepath=filepath))
    subprocess.check_call(cmd)


@pytest.mark.parametrize("pattern, replacement, content", [
    (" \d{3} ", "ASD", "substitute number: 123 is this ok? asdf123qwer"),
    (" 123 ", "ASD", "substitute number: 123 is this ok? asdf123qwer"),
])
def test_sr_single(temp_file, pattern, replacement, content):
    temp_file.write(content)
    original = temp_file.read()
    assert replacement not in original
    # run script
    run_single(pattern=pattern, replacement=replacement, filepath=temp_file)
    substituted = temp_file.read()
    # check that substitutions are OK
    assert "123" in substituted
    assert " 123 " not in substituted
    assert replacement in substituted
