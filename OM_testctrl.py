import socket
import struct
import time
import multiprocessing

#for i2 in range(10):
 #   time.sleep(1)
 #   print 'blop', i2


def timeTrig(cond, cfg):
    while True :
        time.sleep(cfg.value)
        with cond:
            cond.notify()

def delayedChange(cond, cfg):
    time.sleep(4)
    cfg.value = 1.1

 

def diplayTrig(cond):
    while True :
        with cond:
            cond.wait()
            print 'blob'  

if __name__ == '__main__':
   
    tick = multiprocessing.Condition() 
    sendPeriod = multiprocessing.Value('d', 2.0)

    p1 = multiprocessing.Process(target=timeTrig, args=(tick,sendPeriod,))
    p2 = multiprocessing.Process(target=diplayTrig, args=(tick,))
    p3 = multiprocessing.Process(target=delayedChange, args=(tick,sendPeriod,))
    p1.start()
    p2.start()
    p3.start()
    p1.join()
    p2.join()
    p3.join()
