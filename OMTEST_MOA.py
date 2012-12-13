#!/usr/bin/python

import threading
import Queue
import socket
import time
import struct
import subprocess


class MOAjobMaster(threading.Thread):

	def __init__(self, dataQueue, loggerQueue, xferEvent, statEvent, stopEvent):
		super(MOAjobMaster, self).__init__()
		self.dataQueue = dataQueue
		self.loggerQueue = loggerQueue
		self.PCADDR = ('192.168.1.4',10004)
		self.DFTFPGAADDR = ('10.10.1.100', 13108)
		self.FPGAADDR = ('10.10.1.103', 2202)
		#self.DFTFPGAADDR = ('192.168.2.3', 13108)
		#self.FPGAADDR = ('192.168.2.3', 3202)
		self.alive = threading.Event()
		self.alive.set()
		self.recvDict = {}
		self.pktSize = 0
		self.pktTotal = 0
		self.xferPeriod = 0.0
		self.symrate = 3
		self.cfgType = ''
		self.lastRun = False
		self.idle = True
		self.xferEvent = xferEvent
		self.statEvent = statEvent
		self.stopEvent = stopEvent


		


	def run(self):

		xferEvent.clear()
		self.dataSock = socket.socket( socket.AF_INET,socket.SOCK_STREAM)	
		self.dataSock.connect(self.PCADDR)

		self.INIPktGen()
		self.CFGPktGen()

		dataPC = ''
		dataUDP = []

		while self.lastRun == False:
			try:
				
				dataPC = ''

				while dataPC != 'START_XFER':
						dataPC = self.dataSock.recv(10)
						time.sleep(0.5)

				self.idle = False

				#Retrieve configuration
				self.pktSize, self.pktTotal, self.xferPeriod, self.symrate, self.lastRun = struct.unpack('!IIfI?', self.dataSock.recv(17))
				self.cfgType = self.dataSock.recv(3)
				self.loggerPut('MOA configuration received: ' + self.cfgType)

				#Blank and refill Array
				self.recvDict.clear()
				for i in xrange(self.pktTotal):
					self.recvDict[i] = False

				#Configure OM
				if self.cfgType == 'INI':
					self.INIPktGen()
				self.CFGPktGen()

				self.loggerPut('MOA config done, wait 5s')
				time.sleep(5) #OM gets itself sorted out

				#Flush queue
				while self.dataQueue.empty() != True:
					dataUDP = self.dataQueue.get()

				dataUDP = []

				#tell UDP socket to get ready 
				xferEvent.set()
				self.dataQueue.put(['START', self.pktSize, self.pktTotal])

				time.sleep(0.1)

				xferEvent.wait()
				xferEvent.clear()
				self.loggerPut('MOA packet capture starting')

				#Clear Variables
				dataUDP = ['', '']
				msgType = ''
				msgValue = ''
				msgValue_Int = 0

				self.dataSock.send('MOAREADY')

				startTime = time.time()

				while msgType != 'DONE':
					
					dataUDP = self.dataQueue.get()
					msgType = dataUDP[0]
					msgValue = dataUDP[1]
					
					if msgType == 'RECV': 
						msgValue_Int = struct.unpack('!I', msgValue[0:4])
						if msgValue_Int[0] < self.pktTotal:
								self.recvDict[msgValue_Int[0]] = True
						else:
							self.loggerPut('Excessive index value received: ' + str(msgValue_Int[0]))

				if msgValue == 'ALL_DATA_RECV':
					measBitrate = (8*self.pktSize*self.pktTotal)/(time.time()-startTime)
					self.loggerPut('MOA packet capture done, all packets received ')		
				elif msgValue == 'TIMEOUT':
					measBitrate = (8*self.pktSize*self.pktTotal)/(time.time()-10.0-startTime)
					self.loggerPut('MOA packet capture done, UDP socket timed out ')


				droppedPackets = []
				for i in xrange(self.pktTotal):
					if self.recvDict[i] == False:
						droppedPackets.append(i)

				print 'Dropped:', droppedPackets
				self.loggerPut(str(len(droppedPackets)) + ' Packets were dropped')
				self.loggerPut('Measured bitrate is: ' + str(measBitrate) + 'bps')

				
				statEvent.set()


				self.dataSock.send('DONE')
			
			except Queue.Empty:
				continue

		self.loggerPut( 'STOPPING!!!' )
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
		FPGA_IP=0x0A0A0167
		FPGA_PORT=2202

		#ARMADEUS CONFIG
		ARMA_MAC1=0x32A7D885
		ARMA_MAC2=0x6ABF
		ARMA_IP=0x0A0A0103
		ARMA_PORT= 2201

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
		MESSAGE += struct.pack("!I",0x00000509)  #Settings
		MESSAGE += struct.pack("!BH",0x00,10000) 	#Superframe period
		MESSAGE += struct.pack("!BH",0x00,8650) 	#TX start
		MESSAGE += struct.pack("!BH",0x00,9450) 	#TX end
		MESSAGE += struct.pack("!BH",0x00,0) 	#RX start
		MESSAGE += struct.pack("!BH",0x00,8300)  	#RX end
		MESSAGE += struct.pack("!BBB",0x65,0x00,PREAMBLE/4)	#AGC response(4) + HV level(12) + Preamble(8)
		MESSAGE += struct.pack("!BB",self.symrate,0x00)	#TX symbol rate + carrier rate
		MESSAGE += struct.pack("!BB",self.symrate,0x00) 	#RX symbol rate + carrier rate
		MESSAGE += struct.pack("!I",0x000F8001)     #Capture

		sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		sock.sendto(MESSAGE, self.FPGAADDR)
		sock.close


	def loggerPut(self, msgIn):
		msg = 'MOAjobMaster - ' + str(time.time()) + ': ' + msgIn +'\n'
		self.loggerQueue.put(msg)




class UDPDataRecv(threading.Thread):

	def __init__(self, dataQueue, xferEvent):
		super(UDPDataRecv, self).__init__()
		self.dataQueue = dataQueue
		#self.MOAADDR = ('10.10.1.3',10004) 
		self.MOAADDR = ('10.10.1.3',10016) 
		self.alive = threading.Event()
		self.alive.set()
		self.xferEvent = xferEvent
		self.pktTotal = 0
		self.pktSize = 0


	def run(self):

		dataSock = socket.socket( socket.AF_INET,socket.SOCK_DGRAM)
		dataSock.bind(self.MOAADDR)
		dataSock.settimeout(10.0)

		while self.alive.is_set():
			
			dataQ = ['', 0, 0]
			dataUDP = ''
			#Signal from jobmaster to start capturing
			xferEvent.wait()
			xferEvent.clear()
			
			#print 'xferEvent cleared'

			while dataQ[0] != 'START':
				dataQ = self.dataQueue.get()
			
			self.pktSize = dataQ[1]
			self.pktTotal = dataQ[2]
			xferEvent.set()

			#print 'got configuration: PktSize =',self.pktSize, ', PktNo =', self.pktTotal

			
			for i in xrange(self.pktTotal):

				# if i%100 == 0:
				# 	print 'received',i

				try:
					dataUDP = dataSock.recv(self.pktSize+4)
				except socket.timeout:
					self.dataQueue.put(['DONE','TIMEOUT'])
					break;

				self.dataQueue.put(['RECV',dataUDP[0:4]]) 
				if i == self.pktTotal - 1:
					self.dataQueue.put(['DONE','ALL_DATA_RECV'])
					#time.sleep(0.1)	#because otherwise it doesn't work
					#print 'done'

		dataSock.close()

		def join(self, timeout=None):
		
			self.alive.clear()
			threading.Thread.join(self,timeout)





class MOAStatus(threading.Thread):

	def __init__(self, loggerQueue, statEvent):
		super(MOAStatus, self).__init__()
		self.STATADDR = ('10.10.1.3', 2201)
		self.loggerQueue = loggerQueue
		self.alive = threading.Event()
		self.alive.set()
		self.statEvent = statEvent
		self.prev_RX = 0
		self.new_RX = 0
		self.FECcorr = 0
		self.FECfail = False
		self.CRCfail = 0


	def run(self):

		statSock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM ) 
		statSock.bind(self.STATADDR)

		while self.alive.is_set():

			data = statSock.recv(63)
			tempList = []

			if data[0:4] == '#STA':
				tempList = struct.unpack('!I', data[39:43])
				self.FECcorr += tempList[0]
				tempList = struct.unpack('!B', data[45:46])
				self.CRCfail += tempList[0]
				tempList = struct.unpack('!I', data[50:54])
				self.new_RX = tempList[0]

				tempList = struct.unpack('!I', data[50:54])
				if tempList[0] != 0:
					self.FECfail = True
			
			#self.new_RX = time.time()

			if self.statEvent.is_set():

				self.loggerPut( 'MOA end of test status')
				self.loggerPut( str(self.new_RX - self.prev_RX) + ' bytes transmitted' )

				if self.FECfail == False: self.loggerPut( str(self.FECcorr) + ' bytes corrected and no drops were detected since last EOT status' )
				else: self.loggerPut( str(self.FECcorr) + ' bytes corrected and drops were detected since last EOT status' )
				
				self.loggerPut( str(self.CRCfail) + ' bytes did not pass the RX CRC check')
				self.statEvent.clear()

				self.prev_RX = self.new_RX
				self.FECcorr = 0
				self.FECfail = False
				self.CRCfail = 0



		statSock.close()			



	def join(self, timeout=None):
		
		self.alive.clear()
		threading.Thread.join(self,timeout)


	def loggerPut(self, msgIn):
		msg = 'MOAStat - ' + str(time.time()) + ': ' + msgIn + '\n'
		self.loggerQueue.put(msg)





class MOALogClient(threading.Thread):

	def __init__(self, loggerQueue):
		super(MOALogClient, self).__init__()
		self.loggerQueue = loggerQueue
		self.PCADDR = ('192.168.1.4',10014)
		self.alive = threading.Event()
		self.alive.set()

	def run(self):

		queue_data = ''
		logSock = socket.socket( socket.AF_INET,socket.SOCK_STREAM)	
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

	loggerQueue = Queue.Queue()
	dataQueue = Queue.Queue()
	xferEvent = threading.Event()
	statEvent = threading.Event()
	stopEvent = threading.Event()
	stopEvent.clear()
	statEvent.clear()
	
	JOBMASTER = MOAjobMaster(dataQueue, loggerQueue, xferEvent, statEvent, stopEvent)
	UDPRECV = UDPDataRecv(dataQueue, xferEvent)
	STATUS = MOAStatus(loggerQueue, statEvent)
	LOG = MOALogClient(loggerQueue)

	JOBMASTER.start()
	UDPRECV.start()
	STATUS.start()
	LOG.start()

	stopEvent.wait()
	
	JOBMASTER.join()
	UDPRECV.join()
	STATUS.join()
	LOG.join()

	exit()
