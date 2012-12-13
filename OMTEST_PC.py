import struct
import random
import string
from socket import *
import time
import multiprocessing
import threading
import math
import sys




class TestServer(multiprocessing.Process):


	def __init__(self, loggerQueue, orderFile, stopEvent):
		
		super(TestServer, self).__init__()
		self.LOCAL_SOCK_ROA = ('192.168.2.4',10002)
		self.LOCAL_SOCK_MOA = ('192.168.1.4',10004)
		self.alive = multiprocessing.Event()
		self.alive.set()
		self.stopEvent = stopEvent
		self.configType = 'aaa'
		self.payloadType = 'aaaa'
		self.omSymrate = 0
		self.xferPeriod = 0.0
		self.size_mb = 0
		self.pkt_size = 0
		self.loopNo = 0
		self.sample_length = 0
		self.sample_list = []
		self.orderQueue = multiprocessing.Queue()
		self.loggerQueue = loggerQueue
		self.orderFile = orderFile
		self.lastReboot = 0.0
		self.lastRun = False


	
	def run(self):

		self.lastReboot = time.time()
		self.loggerPut( 'Initial program launch at ' + str(self.lastReboot))
		roa_sock = socket(AF_INET, SOCK_STREAM)
		roa_sock.bind(self.LOCAL_SOCK_ROA)
		roa_sock.listen(1)
		roa_conn, roa_addr = roa_sock.accept()
		self.loggerPut( 'Connected to ROA at ' + str(roa_addr))

		moa_sock = socket(AF_INET, SOCK_STREAM)
		moa_sock.bind(self.LOCAL_SOCK_MOA)
		moa_sock.listen(1)
		moa_conn, moa_addr = moa_sock.accept()
		self.loggerPut( 'Connected to MOA at ' + str(moa_addr))

		time.sleep(30)

		self.readOrders()
		

		while self.lastRun == False:

			MOAdata = ''
			orderList = [] # [0] payload type, [1] OM symrate, [2] xfer rate in mbps, [3] total size, [4] packet size, [5] number of loops
			orderList = self.orderQueue.get()
			self.loggerPut('got Order')

			self.payloadType = orderList[0]
			self.omSymrate = orderList[1]
			self.xferPeriod = float((8 * orderList[4])) / float(1000000 * orderList[2])
			self.size_mb = orderList[3]
			self.pkt_size = orderList[4]
			self.orderNo = orderList[5]

			for runNo in xrange(self.orderNo):
				
				self.loggerPut('Starting run ' + str(runNo))

				if self.orderQueue.empty() and (runNo == self.orderNo - 1):
					self.lastRun = True
					self.loggerPut('THIS IS THE LAST RUN!')
				else:
					self.lastRun = False

				if time.time() - self.lastReboot > 3600: #1h elapsed since lastreboot
					self.loggerPut('FPGAs will reload during this run')
					self.configType = 'INI'
					time.sleep(30)
				else: 
					self.loggerPut( str(time.time() - self.lastReboot) + 's elapsed since last reboot')
					self.configType = 'CFG'

				
				if self.payloadType == 'RAND' and runNo == 0:
					self.randomGen()
					self.sample_length = len(self.sample_list)

				self.loggerPut( self.payloadType + ' / ' + 
								self.configType + ' / ' + 
								str(self.omSymrate) + ' / ' + 
								str(self.xferPeriod) + ' / ' + 
								str(self.size_mb) + ' / ' + 
								str(self.pkt_size) + ' / ' + 
								str(self.sample_length) )
				
				#Tell MOA a new test has begun
				moa_conn.send('START_XFER') 
				moa_conn.send(struct.pack('!IIfI?', self.pkt_size, self.sample_length, self.xferPeriod, self.omSymrate, self.lastRun))
				moa_conn.send(self.configType[0:4])
				self.loggerPut( 'MOA configuration sent' )

				#Tell ROA a new test has begun
				roa_conn.send('START_XFER') 
				roa_conn.send(struct.pack('!IIfI?', self.pkt_size, self.sample_length, self.xferPeriod, self.omSymrate, self.lastRun))
				roa_conn.send(self.configType[0:4])
				self.loggerPut( 'ROA configuration sent' )

				MOAdata = ''
				while MOAdata != 'MOAREADY':
					MOAdata = moa_conn.recv(8)
					time.sleep(0.1)

				ROAdata = ''
				while ROAdata != 'ROAREADY':
					ROAdata = roa_conn.recv(8)
					time.sleep(0.1)

				self.loggerPut( 'Transmitting' ) 

				for i in xrange(self.sample_length):
					roa_conn.send(self.sample_list[i])
				
				self.loggerPut( 'Sequence ' + str(runNo) + ' transmitted, awaiting response from MOA' )
				
				while MOAdata != 'DONE':
					MOAdata = moa_conn.recv(4)

				self.loggerPut( 'MOA Response received' )

		self.loggerPut( 'STOPPING IN 10S!!!' )
		time.sleep(10)
		roa_sock.close()
		moa_sock.close()
		self.stopEvent.set()


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


	def readOrders(self):

		with open(self.orderFile,'r+') as CMD_FILE:
			self.loggerPut('Opening order file ' + self.orderFile ) 
		   	for line in CMD_FILE:

		   		if line[0] == '-':
		   			words=line.split(',')
		   			
		   			order=words[0]
		   			symrate=int(words[1])
		   			xferrate=int(words[2])
		   			xfersize=int(words[3])
		   			if int(words[4]) < 1466: pktsize=int(words[4])
		   			else: pktsize = 1466
		   			loopno=int(words[5])

		   			self.loggerPut('Adding order ' + order[1:5] + ' to order queue: ' + 
		   							str(100.0/math.pow(2,symrate)) + 'Mbps, ' +
		   							words[2] + 'Mbps, ' +
		   							words[3] + 'MB, ' +
		   							words[4] + 'B, run ' +
		   							words[5] + ' times') 
		  			
		   			self.orderQueue.put([order[1:5], symrate, xferrate, xfersize, pktsize, loopno])


	def loggerPut(self, msgIn):
		
		msg = 'TestServer - ' + str(time.time()) + ': ' + msgIn + '\n'
		self.loggerQueue.put(msg)




class logServer(multiprocessing.Process):


	def __init__(self, loggerQueue):
		
		super(logServer, self).__init__()
		self.alive = multiprocessing.Event()
		self.alive.set()
		self.loggerQueue = loggerQueue
		#Create onelogfile per day
		self.filename = './omtest_log' + time.strftime('%Y%m%d', time.localtime(time.time())) + '.log'


	def run(self):

		with open(self.filename,'a') as LOG_FILE:

			LOG_FILE.write('\n\n\n\n\n\n')

			data = ''
			ROASproc = threading.Thread(target=self.worker, args=(self.loggerQueue, self.alive, ('192.168.2.4',10012)))
			MOASproc = threading.Thread(target=self.worker, args=(self.loggerQueue, self.alive, ('192.168.1.4',10014)))
			ROASproc.start()
			MOASproc.start()
		
			while self.alive.is_set():

				data = self.loggerQueue.get()
				LOG_FILE.write(data)
				LOG_FILE.flush()

		ROASproc.join()
		MOASproc.join()


	def worker(self, loggerQueue, alive, PCsock):

		recv_data = ''
		LOCAL_SOCK = PCsock
		sock = socket(AF_INET, SOCK_STREAM)
		sock.bind(LOCAL_SOCK)
		sock.listen(1)
		sock_conn, sock_addr = sock.accept()
		loggerQueue.put('logWorker - ' + str(time.time()) + ': ' + 'Connected to ' + str(sock_addr) + '\n')

		while alive.is_set():

			recv_data = sock_conn.recv(1024)
			loggerQueue.put(recv_data)

		sock.close()


	def join(self, timeout=None):
		
		self.alive.clear()
		multiprocessing.Process.join(self,timeout)


	def loggerPut(self, msgIn):
		
		msg = 'logServer - ' + str(time.time()) + ': ' + msgIn + '\n'
		self.loggerQueue.put(msg)















if __name__ == '__main__':

	loggerQueue = multiprocessing.Queue()
	stopEvent = multiprocessing.Event()
	stopEvent.clear()

	DATA = TestServer(loggerQueue, sys.argv[1], stopEvent)
	LOG = logServer(loggerQueue)
	DATA.start()
	LOG.start()
	
	stopEvent.wait()
		
	DATA.join()
	LOG.join()

	exit()

