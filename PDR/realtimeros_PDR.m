clear,close all
rosshutdown
rosinit
clc

lag         = 5;       % lag for the smoothing
threshold   = 3.5;     % number of st.dev. away from the mean to signal
influence   = 0;

rpy = zeros(1,2);
xg = []; yg = [];
ip = []; iv = [];
ip_Location = []; iv_Location = [];
PosX = 0; PosY = 0;
valley = false; peak = false;
trajectory = zeros(1,3);
peakdata = zeros(1,4);
steps = 0;

%% ros
desiredRate = 50;
looptime = 15;
n = desiredRate * looptime;
rate = rosrate(desiredRate);
rate.OverrunAction = 'slip';

%imu
% boolsub = rossubscriber('/initial_position','std_msgs/Bool');
imusub = rossubscriber('/imu/rpy/complementary_filtered','geometry_msgs/Vector3Stamped');
[pospub,posmsg] = rospublisher('/PDR_position','geometry_msgs/Point');

%% main
fprintf('start recording...\r\n')

b = 0.3215;
a=0.02137;
error=0;

fprintf('Get the initial point\r\n')

reset(rate);
for i = 1:n
    
    imudata = receive(imusub);
    rpy(i,:) = [imudata.Vector.X,imudata.Vector.Z];
    yg = [yg imudata.Vector.X];
    
    if i > lag + 5
        
        turn_init = mean(rpy(1:10,2)) - 0.1358;
        RotMat  = [ cos(turn_init)  -sin(turn_init);...
            sin(turn_init)   cos(turn_init)];
        
        % Peak signal detection
        signals = ThresholdingAlgo(yg,lag,threshold,influence);
        if signals(i) == -1
            if yg(i) < yg(i-1)
                iv = yg(i);
                iv_Location = i;
                valley = true;
                signals(i-1) = 0;
            end
        elseif signals(i) == 1 && valley == true
            if yg(i) > yg(i-1)
                ip = yg(i);
                ip_Location = i;
                signals(i-1) = 0;
            elseif yg(i) < yg(i-1)
                peak = true;
            end
        end
        
        if (valley && peak) == true
            % walking freq (between 0.1sec ~ 2sec(50Hz))
            if (ip_Location - iv_Location) >= 10 && (ip_Location - iv_Location) < 100 && (ip-iv) > 0.2
                steps = steps + 1;
                peakdata = [peakdata;iv_Location,iv,ip_Location,ip];
                [StepLength,PosX,PosY] = PosUpdata(iv_Location,iv,ip_Location,ip,rpy,PosX,PosY,a,b,error);
                
                PosRot = [PosX,PosY]*RotMat;                
                posmsg.X = PosRot(1);
                posmsg.Y = PosRot(2);
                posmsg.Z = StepLength;
                send(pospub,posmsg);
               trajectory = [trajectory;StepLength,posmsg.X,posmsg.Y];
                
                fprintf(['steps = ',num2str(steps),' ,sneding goal...\r\n'])
                
            end
            valley = false;
            peak = false;
        end
    end
    waitfor(rate);
end

deltaH = rad2deg(peakdata(2:end,4)-peakdata(2:end,2));

%%
[trajectory(:,2),trajectory(:,3)]*RotMat;


subplot(211),
hold on
plot(yg)
plot(peakdata(2:end,3),yg(peakdata(2:end,3)'),'rv','MarkerFaceColor','r');
plot(peakdata(2:end,1),yg(peakdata(2:end,1)'),'rs','MarkerFaceColor','b');
legend('pitch','theta_m_a_x','theta_m_i_n'), xlabel('Time[sec]'), ylabel('Pitch[rad]')

subplot(212)
plot(-ans(:,2),ans(:,1),'o-'),grid minor;
ylabel('PositionY'),xlabel('PositionX'),legend('trajectory')
title(['Total Distance = ',num2str(sum(trajectory(:,1)))])