from multiprocessing import Process, Queue, Event
from queue import Empty
from time import time, sleep

"""
Sender

1. When send data packet                : Send DATA 
2. When found packet corruption         : DATA Corrupted
3. When sequence number is different    : Wrong Sequence Number
4. When retransmit data packet          : Send DATA Again
5. When success to receive ack packet   : Sent Successfully
6. Timeout                              : (Use writeTimeout function)

Receiver

1. When found packet corruption         : DATA Corrupted
2. When sequence number is different    : Wrong Sequence Number
3. When retransmit ACK packet           : Send ACK Again
4. When success to receive data packet  : Sent ACK
"""

def logFileWorker(q, e, filename):
    logFile = open(filename, 'w')
    logFile.close()

    try:
        while True:
            if e.is_set() and q.empty():
                break

            logFile = open(filename, 'a')

            try:
                while True:
                    logFile.write(q.get(timeout=5))
            except Empty:
                sleep(0.1)
            logFile.close()
    except KeyboardInterrupt:
        logFile = open(filename, 'a')

        try:
            while True:
                logFile.write(q.get(timeout=5))
        except Empty:
            pass
        logFile.close()

    return 0


class logHandler:
    SEND_DATA = 'Send DATA'
    CORRUPTED = 'DATA Corrupted'
    SEND_DATA_AGAIN = 'Send DATA Again'
    WRONG_SEQ_NUM = 'Wrong Sequence Number'
    SUCCESS_ACK = 'Sent Successfully'
    SEND_ACK_AGAIN = 'Send ACK Again'
    SEND_ACK = 'Send ACK'

    def __init__(self):
        self.startflag = False
        self.logQueue = Queue()
        self.endEvent = Event()
        

    def startLogging(self, filename):
        self.filename = filename
        self.loggingProc = Process(target=logFileWorker, args=(self.logQueue, self.endEvent, self.filename))
        self.loggingProc.start()
        if not self.startflag:
            self.startTime = time()
            self.startflag = True
    
    def writePkt(self, pktNum, event):
        if not self.startflag:
            self.startTime = time()
            self.startflag = True

        strToWrite = '{:1.3f} pkt: {} | {}\n'.format(time()-self.startTime, pktNum, event)
        self.logQueue.put(strToWrite)

    def writeAck(self, ackNum, event):
        if not self.startflag:
            self.startTime = time()
            self.startflag = True

        strToWrite = '{:1.3f} ACK: {} | {}\n'.format(time()-self.startTime, ackNum, event)
        self.logQueue.put(strToWrite)

    def writeTimeout(self, ackNum):
        if not self.startflag:
            self.startTime = time()
            self.startflag = True

        strToWrite = '{:1.3f} pkt: {} | {}\n'.format(time()-self.startTime, ackNum, 'TIMEOUT')
        self.logQueue.put(strToWrite)

    def writeEnd(self):
        if self.startflag:
            self.logQueue.put('\n')
            self.logQueue.put('File transfer is finished.\n')
            self.endEvent.set()
            self.loggingProc.join()
        else:
            print("WARNING : logging has not been started!")


