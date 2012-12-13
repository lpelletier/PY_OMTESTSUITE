#!/usr/bin/python
import math

with open('./testCmd.cmd','r+') as CMD_FILE:
   	for line in CMD_FILE:
   		if line[0] != '#':
   			words=line.split(',')
   			
   			order=words[0]
   			symrate=int(words[1])
   			xferrate=int(words[2])
   			xfersize=int(words[3])
   			pktsize=int(words[4])
   			loopno=int(words[5])
  			
  			print 'Order:', order
  			print 'Symbol Rate:', 100.0/math.pow(2,symrate), 'Mbps'
  			print 'Transfer Rate:', xferrate, 'Mbps'
  			print 'Transfer Size:', xfersize, 'MB'
  			print 'Packet Size:', pktsize, 'B'
  			print 'Run test', loopno, 'times'