#!/usr/bin/python

import threading
import Queue
import socket
import time
import struct
import subprocess

class ROAjobMaster(threading.Thread):

	def __init__(self, dataQueue, timerQueue, loggerQueue, statEvent, stopEvent):
		super(ROAjobMaster, self).__init__()
		self.dataQueue = dataQueue
		self.timerQueue = timerQueue
		self.loggerQueue = loggerQueue
		self.PCADDR = ('192.168.2.4',10002)
		self.DFTFPGAADDR = ('10.10.1.100', 13108)
		self.FPGAADDR = ('10.10.1.102', 3202)
		#self.DFTFPGAADDR = ('192.168.2.4', 13108)
		#self.FPGAADDR = ('192.168.2.4', 3202)
		self.EMITTER_ID = '23'
		self.EMITTER_POW = '1'
		self.EMITTER_DIM = '1'
		self.recv_data = ''
		self.pktSize = 0
		self.pktTotal = 0
		self.xferPeriod = 0.0
		self.symrate = 3
		self.cfgType = ''
		self.lastRun = False
		self.idle = True
		self.statEvent = statEvent
		self.stopEvent = stopEvent

		


	def run(self):

		self.dataSock = socket.socket( socket.AF_INET, socket.SOCK_STREAM)	
		self.dataSock.connect(self.PCADDR)
		self.alive = threading.Event()
		self.alive.set()

		self.INIPktGen()
		self.CFGPktGen()
		self.EMCPktGen()

		while self.lastRun == False:
			try:
				while self.recv_data != 'START_XFER':
					self.recv_data = self.dataSock.recv(10)
					time.sleep(0.5)

				self.idle = False

				#Retrieve configuration
				self.pktSize, self.pktTotal, self.xferPeriod, self.symrate, self.lastRun = struct.unpack('!IIfI?', self.dataSock.recv(17))
				self.cfgType = self.dataSock.recv(3)
				self.loggerPut('ROA configuration received: ' + self.cfgType)

				#Forward configuration to UDPTimer
				self.timerQueue.put(self.xferPeriod)
				if self.cfgType == 'INI':
					self.INIPktGen()
				self.CFGPktGen()

				self.loggerPut('ROA Config Done, wait 5s')
				time.sleep(5) #OM gets itself sorted out

				self.dataSock.send('ROAREADY')

				self.loggerPut('Transfer Start')

				for i in xrange(self.pktTotal):
					self.recv_data = self.dataSock.recv(self.pktSize+4)
					if len(self.recv_data) != (self.pktSize+4):
						self.recv_data += self.dataSock.recv(self.pktSize+4 - len(self.recv_data))
					#if (i != 106) and (i != 422) and (i != 585) :
					self.dataQueue.put(self.recv_data)

				while self.idle != True:
					self.idle = self.dataQueue.empty()

				self.loggerPut('Transfer Done')
				time.sleep(5)

				self.statEvent.set()
			
			except Queue.Empty as e:
				continue

		self.loggerPut('STOPPING!!!')
		self.dataSock.close()
		self.stopEvent.set()

	def join(self, timeout=None):
		
		self.alive.clear()
		threading.Thread.join(self,timeout)


	def INIPktGen(self): 

		loadFpga = subprocess.call(['/root/load_fpga_WHOI', '/root/om3x_spartan6_b27.bit'], stdout=subprocess.PIPE)
		#time.sleep(5)


		#FPGA CONFIG
		FPGA_MAC1=0x12345678
		FPGA_MAC2=0x90AB
		FPGA_IP=0x0A0A0166
		FPGA_PORT=3202

		#ARMADEUS CONFIG
		ARMA_MAC1=0x32A7D885
		ARMA_MAC2=0x6ABF
		ARMA_IP=0x0A0A0102
		ARMA_PORT= 3201

		MESSAGE="#INI"
		MESSAGE += struct.pack("!H", 0x0001) #RESET
		MESSAGE += struct.pack("!IH",FPGA_MAC1,FPGA_MAC2)
		MESSAGE += struct.pack("!IH",FPGA_IP,FPGA_PORT)
		MESSAGE += struct.pack("!IH",ARMA_MAC1,ARMA_MAC2)
		MESSAGE += struct.pack("!IH",ARMA_IP,ARMA_PORT)

		sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM ) # UDP
		sock.sendto(MESSAGE, self.DFTFPGAADDR)
		sock.close()

		time.sleep(0.2)


	def CFGPktGen(self): 

		#Modulation settings
		PREAMBLE = 512  #at 2*symbol rate

		MESSAGE="#CFG"
		MESSAGE += struct.pack("!I",0x0000050B)  #Settings
		MESSAGE += struct.pack("!BH",0x00,10000) 	#Superframe period
		MESSAGE += struct.pack("!BH",0x00,8650) 	#TX start
		MESSAGE += struct.pack("!BH",0x00,9450) 	#TX end
		MESSAGE += struct.pack("!BH",0x00,0) 	#RX start
		MESSAGE += struct.pack("!BH",0x00,8300)  	#RX end
		MESSAGE += struct.pack("!BBB",0x75,0x00,PREAMBLE/4)	#AGC response(4) + HV level(12) + Preamble(8)
		MESSAGE += struct.pack("!BB",self.symrate,0x00)	#TX symbol rate + carrier rate
		MESSAGE += struct.pack("!BB",self.symrate,0x00) 	#RX symbol rate + carrier rate
		MESSAGE += struct.pack("!I",0x000F8001)     #Capture

		sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		sock.sendto(MESSAGE, self.FPGAADDR)
		sock.close

	def EMCPktGen(self): 

		MESSAGE="#EMC"
		MESSAGE += struct.pack("!H",0)
		MESSAGE += struct.pack("!cccc",self.EMITTER_ID[0],
								self.EMITTER_ID[1],
								self.EMITTER_POW,
								self.EMITTER_DIM)	

		sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		sock.sendto(MESSAGE, self.FPGAADDR)
		sock.close

	def loggerPut(self, msgIn):
		msg = 'ROAjobMaster - ' + str(time.time()) + ': ' + msgIn + '\n'
		self.loggerQueue.put(msg)




class UDPDataSend(threading.Thread):

	def __init__(self, dataQueue, tickEvent):
		super(UDPDataSend, self).__init__()
		self.dataQueue = dataQueue
		self.MOAADDR = ('10.10.1.3',10016) 
		#self.MOAADDR = ('192.168.2.4',10016) 
		self.alive = threading.Event()
		self.alive.set()
		self.tick = tickEvent


	def run(self):

		data = ''
		dataSock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM)

		while self.alive.is_set():
			self.tick.wait()
			self.tick.clear()
			data = self.dataQueue.get()
			dataSock.sendto(data, self.MOAADDR)

		dataSock.close()

		def join(self, timeout=None):
		
			self.alive.clear()
			threading.Thread.join(self,timeout)





class UDPDataTimer(threading.Thread):

	def __init__(self, timerQueue, tickEvent):
		super(UDPDataTimer, self).__init__()
		self.timerQueue = timerQueue
		self.alive = threading.Event()
		self.alive.set()
		self.tick = tickEvent
		self.sleepValue = 1


	def run(self):

		while self.alive.is_set():
			try:
				time.sleep(self.sleepValue)
				self.tick.set()
				self.sleepValue = self.timerQueue.get_nowait()				

			except Queue.Empty as e:
				continue


	def join(self, timeout=None):
		
		self.alive.clear()
		threading.Thread.join(self,timeout)



class ROAStatus(threading.Thread):

	def __init__(self, loggerQueue, xferEvent):
		super(ROAStatus, self).__init__()
		self.STATADDR = ('10.10.1.2', 3201)
		self.loggerQueue = loggerQueue
		self.alive = threading.Event()
		self.alive.set()
		self.xferEvent = xferEvent
		self.prev_TX = 0
		self.new_TX = 0


	def run(self):

		statSock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM ) 
		statSock.bind(self.STATADDR)

		while self.alive.is_set():

			data = statSock.recv(63)
			tempList = []
			#time.sleep(1)

			if data[0:4] == '#STA':
				tempList = struct.unpack('!I', data[46:50])
				self.new_TX = tempList[0]
			#self.new_TX = time.time()

			if self.xferEvent.is_set():
				self.loggerPut( 'ROA end of test status')
				self.loggerPut( str(self.new_TX - self.prev_TX) + ' Bytes transmitted' )
				self.xferEvent.clear()
				self.prev_TX = self.new_TX



		statSock.close()			



	def join(self, timeout=None):
		
		self.alive.clear()
		threading.Thread.join(self,timeout)


	def loggerPut(self, msgIn):
		msg = 'ROAStat - ' + str(time.time()) + ': ' + msgIn + '\n'
		self.loggerQueue.put(msg)





class ROALogClient(threading.Thread):

	def __init__(self, loggerQueue):
		super(ROALogClient, self).__init__()
		self.loggerQueue = loggerQueue
		self.PCADDR = ('192.168.2.4',10012)
		self.alive = threading.Event()
		self.alive.set()

	def run(self):

		queue_data = ''
		logSock = socket.socket( socket.AF_INET, socket.SOCK_STREAM)	
		logSock.connect(self.PCADDR)

		while self.alive.is_set():
			try:
				queue_data = self.loggerQueue.get()
				logSock.send(queue_data)			

			except Queue.Empty as e:
				continue

		logSock.close()

	def join(self, timeout=None):
		
		self.alive.clear()
		threading.Thread.join(self,timeout)













if __name__ == '__main__':

	timerQueue = Queue.Queue()
	loggerQueue = Queue.Queue()
	dataQueue = Queue.Queue(2048)
	tickEvent = threading.Event()
	statEvent = threading.Event()
	stopEvent = threading.Event()
	stopEvent.clear()
	statEvent.clear()


	JOBMASTER = ROAjobMaster(dataQueue, timerQueue, loggerQueue, statEvent, stopEvent)
	UDPSEND = UDPDataSend(dataQueue, tickEvent)
	UDPTIME = UDPDataTimer(timerQueue, tickEvent)
	STATUS = ROAStatus(loggerQueue, statEvent)
	LOG = ROALogClient(loggerQueue)

	JOBMASTER.start()
	UDPSEND.start()
	UDPTIME.start()
	STATUS.start()
	LOG.start()

	stopEvent.wait()

	JOBMASTER.join()
	UDPSEND.join()
	UDPTIME.join()
	STATUS.join()
	LOG.join()

	exit()
