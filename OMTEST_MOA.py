#!/usr/bin/python

import threading
import Queue
from socket import *
import time
import struct
import subprocess

class TCPDataRecv(threading.Thread):

	def __init__(self, dataQueue, timerQueue, loggerQueue, xferEvent):
		super(TCPDataRecv, self).__init__()
		self.dataQueue = dataQueue
		self.timerQueue = timerQueue
		self.loggerQueue = loggerQueue
		self.PCADDR = ('192.168.2.4',10002)
		#self.DFTFPGAADDR = ('10.10.1.100', 13108)
		#self.FPGAADDR = ('10.10.1.102', 3202)
		self.DFTFPGAADDR = ('192.168.2.4', 13108)
		self.FPGAADDR = ('192.168.2.4', 3202)
		self.EMITTER_ID = '23'
		self.EMITTER_POW = '1'
		self.EMITTER_DIM = '1'
		self.recv_data = ''
		self.pktSize = 0
		self.pktTotal = 0
		self.xferPeriod = 0.0
		self.symrate = 3
		self.cfgType = ''
		self.idle = True
		self.xferEvent = xferEvent

		


	def run(self):

		self.dataSock = socket( AF_INET,SOCK_STREAM)	
		self.dataSock.connect(self.PCADDR)
		self.alive = threading.Event()
		self.alive.set()

		self.INIPktGen()
		self.CFGPktGen()
		self.EMCPktGen()

		while self.alive.is_set():
			try:
				while self.recv_data != 'START_XFER':
						self.recv_data = self.dataSock.recv(10)

				self.idle = False

				#Retrieve configuration
				self.pktSize, self.pktTotal, self.xferPeriod, self.symrate = struct.unpack('!IIfI', self.dataSock.recv(16))
				self.cfgType = self.dataSock.recv(3)

				print 'Configuration Received: ', self.cfgType
				print 'Packet size:', self.pktSize
				print 'Number of Packets:', self.pktTotal
				print 'UDP Xmit Rate: ', self.xferPeriod

				#Forward configuration to UDPTimer
				self.timerQueue.put(self.xferPeriod)
				if self.cfgType == 'INI':
					self.INIPktGen()
				self.CFGPktGen()

				self.loggerPut('Config Done')

				time.sleep(10) #OM gets itself sorted out

				self.loggerPut('Transfer Start')

				for i in xrange(self.pktTotal):
					self.recv_data = self.dataSock.recv(self.pktSize+4)
					if len(self.recv_data) != (self.pktSize+4):
						self.recv_data += self.dataSock.recv(self.pktSize+4 - len(self.recv_data))
					self.dataQueue.put(self.recv_data)

				while self.idle != True:
					self.idle = self.dataQueue.empty()

				self.loggerPut('Transfer Done')
				time.sleep(5)

				self.xferEvent.set()
			
			except Queue.Empty as e:
				continue

	def join(self, timeout=None):
		
		self.alive.clear()
		threading.Thread.join(self,timeout)


	def INIPktGen(self): 

		#loadFpga = subprocess.call(['/root/load_fpga_WHOI', '/root/om3x_spartan6_b27.bit'], stdout=subprocess.PIPE)
		time.sleep(5)


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

		sock = socket( AF_INET, SOCK_DGRAM ) # UDP
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

		sock = socket( AF_INET, SOCK_DGRAM )
		sock.sendto(MESSAGE, self.FPGAADDR)
		sock.close

	def EMCPktGen(self): 

		MESSAGE="#EMC"
		MESSAGE += struct.pack("!H",0)
		MESSAGE += struct.pack("!cccc",self.EMITTER_ID[0],
								self.EMITTER_ID[1],
								self.EMITTER_POW,
								self.EMITTER_DIM)	

		sock = socket( AF_INET, SOCK_DGRAM )
		sock.sendto(MESSAGE, self.FPGAADDR)
		sock.close

	def loggerPut(self, msgIn):
		msg = 'TCPDataRecv - ' + str(time.time()) + ': ' + msgIn
		self.loggerQueue.put(msg)




class UDPDataRecv(threading.Thread):

	def __init__(self, dataQueue, tickEvent):
		super(UDPDataSend, self).__init__()
		self.dataQueue = dataQueue
		#self.MOAADDR = ('10.10.1.3',10004) 
		self.MOAADDR = ('192.168.2.4',10016) 
		self.alive = threading.Event()
		self.alive.set()
		self.tick = tickEvent


	def run(self):

		data = ''
		dataSock = socket( AF_INET,SOCK_DGRAM)

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

		statSock = socket( AF_INET, SOCK_DGRAM ) 
		statSock.bind(self.STATADDR)

		while self.alive.is_set():

			#data = sock.recv(63)
			time.sleep(1)

			#if data[0:4] == '#STA':
			#self.new_TX = struct.unpack('!I', data[46:50])
			self.new_TX = time.time()

			if self.xferEvent.is_set():
				self.loggerPut( str(self.new_TX - self.prev_TX) + ' Bytes transmitted' )
				self.xferEvent.clear()
				self.prev_TX = self.new_TX



		statSock.close()			



	def join(self, timeout=None):
		
		self.alive.clear()
		threading.Thread.join(self,timeout)


	def loggerPut(self, msgIn):
		msg = 'ROAStat - ' + str(time.time()) + ': ' + msgIn
		self.loggerQueue.put(msg)





class ROALogClient(threading.Thread):

	def __init__(self, loggerQueue):
		super(ROALogClient, self).__init__()
		self.loggerQueue = loggerQueue
		self.PCADDR = ('192.168.2.4',10014)
		self.alive = threading.Event()
		self.alive.set()

	def run(self):

		queue_data = ''
		logSock = socket( AF_INET,SOCK_STREAM)	
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
	xferEvent = threading.Event()
	
	TCPDataRecvProc = TCPDataRecv(dataQueue, timerQueue, loggerQueue, xferEvent)
	UDPDataSendproc = UDPDataSend(dataQueue, tickEvent)
	UDPDataTimerProc = UDPDataTimer(timerQueue, tickEvent)
	ROALogClientProc = ROALogClient(loggerQueue)

	TCPDataRecvProc.start()
	UDPDataSendproc.start()
	UDPDataTimerProc.start()
	ROALogClientProc.start()


	while True:
		time.sleep(30)
