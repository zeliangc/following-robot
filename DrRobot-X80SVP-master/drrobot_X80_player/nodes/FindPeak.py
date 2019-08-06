#!/usr/bin/env python


import rospy
import numpy as np
import pylab
from math import cos,sin
from geometry_msgs.msg import Vector3Stamped, Point
import matplotlib.pyplot as plt

lag = 5	# lag for the smoothing
threshold = 3.5	# number of st.dev. away from the mean to signal
influence = 0

PosX = 0
PosY = 0
rpy=[]
xg = []
yg = []
valley = False
peak = False
trajectory = np.zeros([1,3])
peakdata = np.zeros([1,4])
steps = 0
i = 0


class findpeak():
	def __init__(self):
		rospy.init_node('realtime_FindPeak', anonymous=True)
		self.cmd_vel_pub = rospy.Publisher('goal_position', Point, queue_size=1)

		self.rate = rospy.Rate(25)		
		print('start recording...')
		rospy.sleep(1)

		self.position_subscriber = rospy.Subscriber('/imu/rpy/complementary_filtered', Vector3Stamped, self.callback)

		self.vector3 = Vector3Stamped()

	def callback(self,imudata):
		global xg,yg,rpy ,i,signals,valley,peak	
		self.vector3 = imudata
		self.vector3.vector.x = round(self.vector3.vector.x,4)
		self.vector3.vector.z = round(self.vector3.vector.z,4)
		print(self.vector3.vector.x,self.vector3.vector.z)
		#return self.vector3.vector.x,self.vector3.vector.z

		while (i < 50) :
		#for i in range(1, 500):
			    #i += 1	
			    rpy.append([self.vector3.vector.x,self.vector3.vector.z])		
			    #print(i,rpy[i][:])
			    print(i,rpy[i][:])			    			    
			    xg.append(i)			   
			    yg.append(self.vector3.vector.x)
			    #print(xg[i],yg[i])			    
			    
			    i += 1

			    if len(xg) > lag + 5:
				
				#print(len(xg))
				turn_init = np.mean(rpy[1:10][2])
				c, s = np.cos(turn_init), np.sin(turn_init)
				RotMat = np.array(((c,-s), (s, c)))
				#print(np.rad2deg(turn_init))
				
				# Peak signal detection 
				signals = ThresholdingAlgo(yg, lag, threshold, influence)
				print(i,signals[i-1])				
				#print(np. shape(signals))

				if (signals[i-1] == -1):
				    if (yg[i] < yg[i - 1]):
					iv = yg[i]
					iv_Location = i
					valley = True
					signals[i - 1] = 0
				
				elif (signals[i-1] == 1) and (valley == True):
				     if (yg[i] > yg[i - 1]):
					ip = yg[i]
					ip_Location = i
					signals[i - 1] = 0

				     elif (yg[i] < yg[i - 1]):
					 peak = True
					    
					    
				#print(signals)
				if (valley and peak) == True:
					# walking freq (between 0.1sec ~ 2sec(50Hz))
				   if (ip_Location - iv_Location) >= 10 and (ip_Location - iv_Location) < 100 and (ip-iv) > 0.2:
					steps = steps + 1
					print steps

					#peakdata = mcat([peakdata, OMPCSEMI, iv_Location, iv, ip_Location, ip])
					[StepLength, PosX, PosY] = PosUpdata(iv_Location, iv, ip_Location, ip, rpy, PosX, PosY)
					#trajectory = mcat([trajectory, OMPCSEMI, StepLength, PosX, PosY])

					posmsg = Point()
					PosRot = ([PosX, PosY]) * RotMat
					posmsg.X = PosRot[1]
					posmsg.Y = PosRot[2]
					posmsg.Z = 0

					cmd_vel_pub.publish(posmsg)
					print('sneding goal...\\r\\n')

						    
				   valley = False
				   peak = False

		plt.figure(1)
		plt.subplot(211)
		plt.plot(xg,yg)
		plt.subplot(212)
		#plt.plot(signals)

		plt.pause(0.001)		
		plt.show()
		#print(np. shape(signals))
		i = 0
		xg=[]
		yg=[]
		rpy=[]
		


	#position_subscriber = rospy.Subscriber('/imu/rpy/complementary_filtered', Vector3Stamped, callback, queue_size=1)
        



def ThresholdingAlgo(y, lag, threshold, influence):
	signals = np.zeros(len(y))
	filteredY = np.array(y)
	avgFilter = [0]*len(y)
	stdFilter = [0]*len(y)
	avgFilter[lag - 1] = np.mean(y[0:lag])
	stdFilter[lag - 1] = np.std(y[0:lag])
	for k in range(lag, len(y)):
		if abs(y[k] - avgFilter[k-1]) > threshold * stdFilter [k-1]:
		    if y[k] > avgFilter[k-1]:
			signals[k] = 1
		    else:
			signals[k] = -1
		        filteredY[k] = influence * y[k] + (1 - influence) * filteredY[k-1]
		        avgFilter[k] = np.mean(filteredY[(k-lag+1):k+1])
			stdFilter[k] = np.std(filteredY[(k-lag+1):k+1])
		else:
		    signals[k] = 0
		    filteredY[k] = y[k]
		    avgFilter[k] = np.mean(filteredY[(k-lag+1):k+1])
		    stdFilter[k] = np.std(filteredY[(k-lag+1):k+1])
	#return dict(signals = np.asarray(signals),avgFilter = np.asarray(avgFilter),stdFilter = np.asarray(stdFilter))
	return signals 

def PosUpdata(Min_PeakLocation,Min_PkValue,Max_PeakLocation,Max_PkValue,rpy,PositionX,PositionY):
	pos_start = Min_PeakLocation
	pos_end = Max_PeakLocation

	# orientation (yaw)
	YawSin = np.mean( rpy[pos_start:pos_end][2])	#(unit:rad)
	YawCos = np.mean( rpy[pos_start:pos_end][2])

	deltaH = np.rad2deg(Max_PkValue - Min_PkValue)
	# step length estimation
	StepLength = deltaH * 0.02137 + 0.494

	# position update
	PosX = PositionX + StepLength * cos(YawCos)	#(unit:rad)
	PosY = PositionY + StepLength * sin(YawSin)
	print(StepLength,PosX,PosY)
	return StepLength,PosX,PosY


	


if __name__=="__main__":
    try:
	x = findpeak()

	rospy.spin()
    except:
        rospy.loginfo("Out-and-Back node terminated.")
	
			
