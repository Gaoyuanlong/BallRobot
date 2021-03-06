try:
    import Adafruit_BBIO.PWM as PWMoutput
except ImportError:
    print "*********** Using stubbed PWM module ************"
    import PWMStubs as PWMoutput
    
from time import sleep
import threading
import collections
import numpy
import InvertPort
import Queue
import struct
import Globals

class Motor(threading.Thread):
    pastSpeeds = None
    myMotorNumber = None
    myDesiredSpeed = 0
    myInvertPort = None
    myPWMPort = None
    myPeriod = None
    myDirInverted = None
    myMotorDeadband = 0.0
    myDebug = None
    myTelemQueue = None
    myNotificationQueue = None

    def __init__(self, pwmPort, invertPortNumber, inverted, motorNumber, PWMFreq, telemQueue, notificationQueue ,dirInverted = False,period=0.02,filterDepth = 10, debug=False):
        self.myMotorNumber = motorNumber
	print "Motor " + str(self.myMotorNumber) + " thread started"
        self.myInvertPort = InvertPort.InvertPort(str(invertPortNumber),debug)
        self.pastSpeeds =  collections.deque(maxlen=filterDepth)
        self.myPWMPort = pwmPort
        PWMoutput.start(self.myPWMPort,50,PWMFreq,inverted)
        super(Motor, self).__init__()
        self.daemon = True 
        self.myPeriod=period
        self.myDebug = debug
	self.myTelemQueue = telemQueue
	self.myNotificationQueue = notificationQueue
	if dirInverted:
	    print "Motor " + str(self.myMotorNumber) + " is inverted"
	    self.myDirInverted = -1
	else:
            print "Motor " + str(self.myMotorNumber) + " is not inverted"
            self.myDirInverted = 1
    def set_speed(self,speed):
        #from open office f(x) =  - 58.2750582751x^4 + 221.8337218337x^3 - 321.3286713287x^2 + 258.7140637141x - 0.8391608392
        #self.myDesiredSpeed = (speed*(100.0-self.myMotorDeadband))
        self.myDesiredSpeed = -58.2750582751*(abs(speed)**4) + 221.8337218337*(abs(speed)**3) - 321.3286713287*(abs(speed)**2) + 258.7140637141*abs(speed) - 0.8391608392
        if speed < 0.0:
            self.myDesiredSpeed = -self.myDesiredSpeed
        if(self.myDesiredSpeed>100.0):
            print "ERROR current speed out of range +" + str(self.myDesiredSpeed)
            self.myDesiredSpeed=100.0
        if(self.myDesiredSpeed<-100.0):
            print "ERROR current speed out of range -" + str(self.myDesiredSpeed)
            self.myDesiredSpeed=-100.0
        self.myTelemQueue.put(struct.pack('>LLffL',0xdeadbeef,self.myMotorNumber+Globals.MOTOR_NOTIFICATION_OFFSET,self.myDesiredSpeed,float(speed),0x1badcafe))
        self.myNotificationQueue.put(self.myMotorNumber+Globals.MOTOR_NOTIFICATION_OFFSET)
        
    def run(self):
        while 1:
            #TODO: better filter design
            self.pastSpeeds.append(self.myDesiredSpeed)
            currentSpeed = numpy.mean(self.pastSpeeds)
            currentSpeed = self.myDesiredSpeed
            if(self.myDesiredSpeed>100.0):
              print "ERROR current speed out of range +" + str(self.myDesiredSpeed)
              self.myDesiredSpeed=100.0
            if(self.myDesiredSpeed<-100.0):
              print "ERROR current speed out of range -" + str(self.myDesiredSpeed)
              self.myDesiredSpeed=-100.0
            PWMoutput.set_duty_cycle(self.myPWMPort,abs(self.myDesiredSpeed)+self.myMotorDeadband)
            if(self.myDesiredSpeed < 0.0):
                self.myInvertPort.invert()
            else:
                self.myInvertPort.not_invert()
            if(self.myDebug):
                print "Motor: " + str(self.myMotorNumber) + " current speed: " + '%+10f' % self.myDesiredSpeed
            sleep(self.myPeriod)
