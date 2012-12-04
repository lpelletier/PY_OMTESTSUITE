import struct
import random
import string
import socket
import multiprocessing

def randomGen(ctrl_pipe, rand_data_queue):

  cycleNo = 0

  while 1:

      size = 0
      randomstr = ''
      recv_data = ''

      while recv_data != 'START':
        recv_data = ctrl_pipe.recv()

      #GENDATA RECEIVED
      size_mb = ctrl_pipe.recv()
      pkt_size = ctrl_pipe.recv()
      print size_mb
      print pkt_size

      size = int( 1024 * 1024 * size_mb )
      randomstr = ''.join([random.choice(string.printable) for i in xrange(size)])

      rand_data_queue.put( size_mb )
      rand_data_queue.put( pkt_size )
      rand_data_queue.put( len(randomstr)/pkt_size )

      for i in xrange(len(randomstr)/pkt_size):
        rand_data_queue.put( struct.pack("!I", i) + randomstr[(pkt_size*i):(pkt_size*(i+1))] )

      cycleNo += 1
      print 'GEN ', cycleNo, 'COMPLETE'


def ROAserver(ROAs_data_queue):

  LOCAL_SOCK = ('192.168.2.4',5566) #ROA

  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # UDP
  sock.bind(LOCAL_SOCK)
  sock.listen(1)
  roa_conn,roa_addr = sock.accept()
  print 'Connected to ', roa_addr

  while 1:

    recv_data = ''

    size_mb = ROAs_data_queue.get()
    pkt_size = ROAs_data_queue.get()
    sample_length = ROAs_data_queue.get()

    print size_mb, " / ", pkt_size, " / ", sample_length
    roa_conn.send(struct.pack("!II", sample_length, pkt_size))

    for i in xrange(sample_length):
        roa_conn.send(ROAs_data_queue.get())
    print 'Done'

    print roa_conn.recv(4)

  roa_conn.close()
  s.close()

#def MOAserver



######################## MAIN #########################

if __name__ == '__main__':

  gen2sendQ = multiprocessing.Queue()
  ConfigC, ConfigP = multiprocessing.Pipe(duplex = False)

  p1 = multiprocessing.Process(target=randomGen, args=(ConfigC,gen2sendQ,))
  p2 = multiprocessing.Process(target=ROAserver, args=(gen2sendQ,))
  ConfigP.send('START')
  ConfigP.send(20)
  ConfigP.send(1466)
  p1.start()
  p2.start()
  p1.join()
  p2.join()

  