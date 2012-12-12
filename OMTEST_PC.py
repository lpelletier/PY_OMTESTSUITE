import struct
import random
import string
from socket import *
import time
import multiprocessing


class ROAServer(multiprocessing.Process):


	def __init__(self, orderQueue, loggerQueue):
		
		super(ROAServer, self).__init__()
		self.LOCAL_SOCK_ROA = ('192.168.2.4',10002)
		self.LOCAL_SOCK_MOA = ('192.168.2.4',10004)
		self.alive = multiprocessing.Event()
		self.alive.set()
		self.configType = 'aaa'
		self.payloadType = 'aaaa'
		self.omSymrate = 0
		self.xferPeriod = 0.0
		self.size_mb = 0
		self.pkt_size = 0
		self.sample_length = 0
		self.sample_list = []
		self.orderQueue = orderQueue
		self.loggerQueue = loggerQueue


	
	def run(self):

		sock = socket(AF_INET, SOCK_STREAM)
		sock.bind(self.LOCAL_SOCK_ROA)
		sock.listen(1)
		
		roa_conn, roa_addr = sock.accept()
		self.loggerPut( 'Connected to ' + str(roa_addr))

		while self.alive.is_set():

			orderList = [] # [0] payload type, [1] config type, [2] OM symrate, [3] xfer rate in mbps, [4] total size, [5] packet size 
			orderList = self.orderQueue.get()

			self.payloadType = orderList[0]
			self.configType = orderList[1]
			self.omSymrate = orderList[2]
			self.xferPeriod = float((8 * orderList[5])) / float(1000000 * orderList[3])
			self.size_mb = orderList[4]
			self.pkt_size = orderList[5]
			
			self.randomGen()
			self.sample_length = len(self.sample_list)

			self.loggerPut( self.payloadType + ' / ' + 
							self.configType + ' / ' + 
							str(self.omSymrate) + ' / ' + 
							str(self.xferPeriod) + ' / ' + 
							str(self.size_mb) + ' / ' + 
							str(self.pkt_size) + ' / ' + 
							str(self.sample_length) )
			
			roa_conn.send('START_XFER') 
			roa_conn.send(struct.pack('!IIfI', self.pkt_size, self.sample_length, self.xferPeriod, self.omSymrate))
			roa_conn.send(self.configType[0:4])

			for i in xrange(self.sample_length):
				roa_conn.send(self.sample_list[i])
			
			self.loggerPut( 'ROAServer Done' )

		sock.close()


	def join(self, timeout=None):
		
		self.alive.clear()
		multiprocessing.Process.join(self,timeout)


	def randomGen(self):

		size = 0
		randomstr = ''
		recv_data = ''

		size = int( 1024 * 1024 * self.size_mb )
		randomstr = ''.join([random.choice(string.printable) for i in xrange(size)])

		for i in xrange(len(randomstr)/self.pkt_size):
			self.sample_list.append( struct.pack("!I", i) + randomstr[(self.pkt_size*i):(self.pkt_size*(i+1))] )

		self.loggerPut('GEN COMPLETE')


	def loggerPut(self, msgIn):
		
		msg = 'ROAServer - ' + str(time.time()) + ': ' + msgIn
		self.loggerQueue.put(msg)






class logServer(multiprocessing.Process):


	def __init__(self, loggerQueue):
		
		super(logServer, self).__init__()
		self.alive = multiprocessing.Event()
		self.alive.set()
		self.loggerQueue = loggerQueue
		self.filename = './omtest_log.log'


	def run(self):

		data = ''
		ROASproc = multiprocessing.Process(target=self.worker, args=(self.loggerQueue, self.alive, 10014,))
		#MOASproc = multiprocessing.Process(target=self.worker, args=(tick,))
		ROASproc.start()
		#MOASproc.start()
		
		while self.alive.is_set():

			data = self.loggerQueue.get()
			with open(self.filename,'a') as LOG_FILE:
				LOG_FILE.write(data + '\n')

		ROASproc.join()
		#MOASproc.join()


	def worker(self, loggerQueue, aliveEvent, port):

		recv_data = ''
		LOCAL_SOCK = ('192.168.2.4',port)
		sock = socket(AF_INET, SOCK_STREAM)
		sock.bind(LOCAL_SOCK)
		sock.listen(1)
		sock_conn, sock_addr = sock.accept()

		while aliveEvent.is_set():

			recv_data = sock_conn.recv(1024)
			loggerQueue.put(recv_data)

		sock.close()


	def join(self, timeout=None):
		
		self.alive.clear()
		multiprocessing.Process.join(self,timeout)


	def loggerPut(self, msgIn):
		
		msg = 'logServer.ROAserver - ' + str(time.time()) + ': ' + msgIn
		self.loggerQueue.put(msg)







if __name__ == '__main__':

	orderQueue = multiprocessing.Queue()
	loggerQueue = multiprocessing.Queue()
	#[0] payload type, [1] config type, [2] OM symrate, [3] xfer rate in mbps, [4] total size, [5] packet size 

	testOrder = ['RAND', 'CFG', 3, 1, 5, 1400]

	DATA = ROAServer(orderQueue=orderQueue,loggerQueue=loggerQueue)
	LOG = logServer(loggerQueue=loggerQueue)
	DATA.start()
	LOG.start()
	orderQueue.put(testOrder)
	
	while True:
		time.sleep(30)