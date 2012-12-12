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
		self.PCADDR = ('192.168.2.4',10002)
		self.DFTFPGAADDR = ('10.10.1.100', 13108)
		self.FPGAADDR = ('10.10.1.102', 3202)
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

		self.dataSock = socket( AF_INET,SOCK_STREAM)	
		self.dataSock.connect(self.PCADDR)
		self.alive = threading.Event()
		self.alive.set()

		__INIPktGen()
		__CFGPktGen()
		__EMCPktGen()


	def run(self):

		while self.alive.isSet():
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
					__INIPktGen()
				__CFGPktGen()

				__loggerPut('Config Done')

				time.sleep(10) #OM gets itself sorted out

				__loggerPut('Transfer Start')

				for i in xrange(self.pktTotal):
					self.recv_data = self.dataSock.recv(self.pktSize)
					self.dataQueue.put(self.recv_data)

				while self.idle != True:
					self.idle = self.dataQueue.empty()

				__loggerPut('Transfer Done')
				time.sleep(5)

				self.xferDone.set()
			
			except Queue.Empty as e:
				continue

	def join(self, timeout=None):
		
		self.alive.clear()
		threading.Thread.join(self,timeout)


	def __INIPktGen(self): 

		loadFpga = subprocess.call(['/root/load_fpga_WHOI', '/root/om3x_spartan6_b27.bit'], stdout=subprocess.PIPE)

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
		MESSAGE += pack("!H", 0x0001) #RESET
		MESSAGE += pack("!IH",FPGA_MAC1,FPGA_MAC2)
		MESSAGE += pack("!IH",FPGA_IP,FPGA_PORT)
		MESSAGE += pack("!IH",ARMA_MAC1,ARMA_MAC2)
		MESSAGE += pack("!IH",ARMA_IP,ARMA_PORT)

		sock = socket( AF_INET, SOCK_DGRAM ) # UDP
		sock.sendto(MESSAGE, self.DFTFPGAADDR)
		sock.close()

		time.sleep(0.2)


	def __CFGPktGen(self): 

		#Modulation settings
		PREAMBLE = 512  #at 2*symbol rate

		MESSAGE="#CFG"
		MESSAGE += pack("!I",0x0000050B)  #Settings
		MESSAGE += pack("!BH",0x00,10000) 	#Superframe period
		MESSAGE += pack("!BH",0x00,8650) 	#TX start
		MESSAGE += pack("!BH",0x00,9450) 	#TX end
		MESSAGE += pack("!BH",0x00,0) 	#RX start
		MESSAGE += pack("!BH",0x00,8300)  	#RX end
		MESSAGE += pack("!BBB",0x75,0x00,PREAMBLE/4)	#AGC response(4) + HV level(12) + Preamble(8)
		MESSAGE += pack("!BB",self.om_settings['bitrate'],0x00)	#TX symbol rate + carrier rate
		MESSAGE += pack("!BB",self.om_settings['bitrate'],0x00) 	#RX symbol rate + carrier rate
		MESSAGE += pack("!I",0x000F8001)     #Capture

		sock = socket( AF_INET, SOCK_DGRAM )
		sock.sendto(MESSAGE, self.FPGAADDR)
		sock.close

	def __EMCPktGen(self): 

		MESSAGE="#EMC"
		MESSAGE += pack("!H",0)
		MESSAGE += pack("!cccc",self.EMITTER_ID[0],
								self.EMITTER_ID[1],
								self.EMITTER_POW,
								self.EMITTER_DIM)	

		sock = socket( AF_INET, SOCK_DGRAM )
		sock.sendto(MESSAGE, self.FPGAADDR)
		sock.close

	def __loggerPut(self, msgIn):
		msg = 'TCPDataRecv - ' + str(time.time()) + ': ' + msgIn
		self.loggerQueue.put(msg)




class UDPDataSend(threading.Thread):

	def __init__(self, dataQueue, tickEvent):
		super(UDPDataSend, self).__init__()
		self.dataQueue = dataQueue
		self.MOAADDR = ('10.10.1.3',10004)
		self.data = ''
		self.dataSock = socket( AF_INET,SOCK_DGRAM)
		self.alive = threading.Event()
		self.alive.set()
		self.tick = tickEvent


	def run(self):

		while self.alive.isSet():
			self.tick.wait()
			self.tick.clear()
			self.data = self.dataQueue.get()
			self.dataSock.sendto(self.data, self.MOAADDR)

			
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

		while self.alive.isSet():
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
		self.statSock = socket( AF_INET, SOCK_DGRAM ) 
		self.statSock.bind(self.STATADDR)
		self.prev_TX = 0
		self.new_TX = 0


	def run(self):

		while self.alive.isSet():

			data = sock.recv(63)

			if data[0:4] == '#STA':
				self.new_TX = struct.unpack('!I', data[46:50])

				if self.xferEvent.isSet():
					__loggerPut( str(self.new_TX - self.prev_TX) + ' Bytes transmitted' )
					self.xferEvent.clear()
					self.prev_TX = self.new_TX



		self.statSock.close()			



	def join(self, timeout=None):
		
		self.alive.clear()
		threading.Thread.join(self,timeout)


	def __loggerPut(self, msgIn):
		msg = 'ROAStat - ' + str(time.time()) + ': ' + msgIn
		self.loggerQueue.put(msg)





class ROALogClient(threading.Thread):

	def __init__(self, loggerQueue):
		super(ROALogClient, self).__init__()
		self.loggerQueue = loggerQueue
		self.PCADDR = ('192.168.2.4',10006)
		self.queue_data = ''
		self.alive = threading.Event()
		self.alive.set()
		self.logSock = socket( AF_INET,SOCK_STREAM)	
		self.logSock.connect(self.PCADDR)


	def run(self):

		while self.alive.isSet():
			try:
				self.queue_data = self.loggerQueue.get()
				self.logSock.send(self.queue_data)			

			except Queue.Empty as e:
				continue

		self.logSock.close()

	def join(self, timeout=None):
		
		self.alive.clear()
		threading.Thread.join(self,timeout)













if __name__ == '__main__':

	timerQueue = Queue.Queue()
	loggerQueue = Queue.Queue()
	dataQueue = Queue.Queue(2048)
	xferTick = threading.Event()
	xferDone = threading.Event()
	

	TCPDataRecvProc = TCPDataRecv(dataQueue, configQueue, timerQueue)
	UDPDataSendProc = UDPDataSend(dataQueue, xferTick)
	UDPDataTimerProc = UDPDataTimer(timerQueue, xferTick)

	TCPDataRecvProc.start()
	UDPDataSendProc.start()
	UDPDataTimerProc.start()

	while True:
		time.sleep(30)
		print 'Zzzzzzz'
