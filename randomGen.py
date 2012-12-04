import random
import sys
import string

def randomGen(FILENAME, SIZE_MB):

    size = 1024 * 1024 * SIZE_MB

    with open(FILENAME,'w+b') as RANDOM_FILE:
        for i in xrange(size):
            RANDOM_FILE.write(random.choice(string.printable))