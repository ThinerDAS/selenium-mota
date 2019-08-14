#!/usr/bin/python -i

import time
import sys
from headlessmota import MotaInstance

# this script is for yinhe

if len(sys.argv) < 2:
    print 'Usage:\n\t', sys.argv[0], 'path_to_yinhe'
    exit(1)

# create a magic tower session
mt = MotaInstance(sys.argv[1])
# we take fake wall and hinting npc directly
mt.eat_set = set([444, 545])

# kill the first slime
mt.move_only_directly(4, 16)
# grab everything grabable
mt.simple_grab_all()
# this is the save data
print mt.savedata()
