import struct
import random
import string
import socket

def randomGen(size_mb):

  global pktlist 

  size = int( 1024 * 1024 * size_mb )
  randomstr = ''.join([random.choice(string.printable) for i in xrange(size)])

  for i in xrange(len(randomstr)/1466):
    pktlist.append( struct.pack("!I", i) + randomstr[(1466*i):(1466*(i+1))] )



######################## MAIN #########################

if __name__ == '__main__':

  pktlist = list()
  randomGen(0.1)
  print 'RANDOMGEN DOME'
  print len(pktlist)

  for i in xrange(4):
    tmpstr = pktlist[i]
    print len(pktlist[i])


  #NETWORK INIT
  LOCAL_SOCK = ('192.168.2.4',5566)

  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # UDP
  sock.bind(LOCAL_SOCK)
  sock.listen(2)

  conn,addr = sock.accept()
  print 'Connected to ', addr

  conn.send(struct.pack("!II", len(pktlist), len(pktlist[i])))

  for object in pktlist[:]:
    conn.send(object)

  conn.close
  print 'Done'






  #SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  #SOCK.bind(('127.0.0.1', 5566))
  #SOCK.close()
  


  #SOCK.send()