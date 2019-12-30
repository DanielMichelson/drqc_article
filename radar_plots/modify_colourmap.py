#!/usr/bin/env python
'''
Copyright (C) 2019 The Crown (i.e. Her Majesty the Queen in Right of Canada)

This file is an add-on to RAVE.

RAVE is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

RAVE and this software are distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with RAVE.  If not, see <http://www.gnu.org/licenses/>.

'''
##
# 


## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2019-08-16

import sys, os
import _raveio
import rave_ql
import numpy as np


def loadLines(fstr, reverse=True):
    fd = open(fstr)
    LINES = fd.readlines()
    fd.close()
    return LINES


# Input lists are ordered correctly
def shuffle(lists, breakpoint=162):
    rest = (256-breakpoint)
    stepb = 128./breakpoint
    stepr = 128./rest

    bl = []
    for i in range(breakpoint):
        bl.append(lists[127 - int(round(i*stepb))])
    bl.reverse()
    rl = []
    for i in range(rest):
        rl.append(lists[127 + int(round(i*stepr))])
    #rl.reverse()

    lists = bl + rl
    return lists
    ol = []
    for l in lists:
        for i in l:
            ol.append(i)
    return ol


def moleron():
    l = loadLines("oleron.txt")
    l = shuffle(l, 162)
    fd = open("moleron.txt", "w")
    for line in l:
        fd.write(line)
    fd.close()


def mroma():
    l = loadLines("roma.txt")
    l = shuffle(l, 64)
    fd = open("mroma.txt", "w")
    for line in l:
        fd.write(line)
    fd.close()



if __name__=="__main__":
#    moleron()
    mroma()
