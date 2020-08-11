from direct.gui.DirectGui import DirectEntry
from framework.latentmodule import LatentModule
import panda3d.core
from sys import exit, stdout
#from time import time, sleep
import time 
import pylsl.pylsl as pylsl
import scipy as sp
import numpy as np
from scipy import signal as sig

    
#MARKER DICTIONARY

MARKER   = {"experimentStart"   : 10000,
            "L"                 : 21000,
            "R"                 : 22000,
            "beginT"            : 31000,
            "endT"              : 32000,

            "beginImagery"      : 11111,
            "endImagery"        : 88888,

            "blockStart"        : 41001,
            "blockEnd"          : 41002,

            "RELAX"             : 50000,
            "putPlus"           : 60000,
            "putImagery"        : 61000,

            "experimentEnd"     : 90000}
            
TODISPLAY = {'L'     :"Left",
            'R'      : "Right"}      

SEQBARS = [0,0,1,0,1,1,0,1,0,0,1,1,1,0,0,1,1,0,0,1,1,0,1,0,1,1,0,1,0,0]



# channels FC3, C3, CP3 on the left side and FC4, C4, CP4 on the right side 
# in each entry, the first value is the location of one of the above channels 
# the other 4 are the neighboring channels
# this info is used for spatial filtering of the recorded EEG data
channelLaplaceMatrix = [[12, 42, 46, 47, 51],[14, 43, 48, 49, 53],
                        [42, 3, 7, 8, 12],[43, 5, 9, 10, 14],
                        [51, 12, 17, 18, 23], [53, 14, 19, 20, 25]]
     
           


class Main(LatentModule):
    def __init__(self):
        LatentModule.__init__(self)

        self.nsamplesOrig = 5000           # 100 Number of samples to collect for online methods (worth 0.5 seconds of data)
        self.srateToBe = 100    # sampling rate where the processing is done 
        self.ratDec = 5   # 10 this is to downsample in two steps
        self.ratDec1 = 10   # 10 this is to downsample in two steps

        self.bands = np.asarray([7, 30]) #frequency range to filter in 

        self.trialsInBlock = 10    
        self.imageryTime = 3    # this is the time for which the subject is doing imagery
        self.wait_duration = 5  #  between two consecutive trials 

        self.discardTime = 0.12 # this is the amount of delay in the eeg system 

        self.maxVar = 0.5     # to adjust the bar heights
        self.distVar = 0.02

        self.fontFace = "arial.ttf"
        self.fontSize = 0.07
        self.textColor = (.8, .8, .5, 1)
        self.blockPauseText = "Please take a break, and tell the experimenter \n when you are ready to continue."
        self.blockEndText = "You have completed this block of the experiment. \n Please take a break, and tell the experimenter \n when you are ready to move on to the next part."

        self.finalText = "You have completed the experiment. \n Well done!."


        self.stimulus_set = ['L','R']  
        self.rectHeight = [0,0] 
        self.cue = None
        self.cue1 = None
        self.cue2 = None

        ## Set up variables for EEG
        self.eegsystem = 'BrainProducts'
        self.chansLeft = [12, 42, 51] #[8,42,18,12,47,51]   #11, 12]#[20, 13]   , 5, 6, 11, 12        # chans[0] - chan to use; chans[1] - chan to re-ref to !!!!!!!!! TO CHECK
        self.chansRight = [14, 43, 53] #[9,14,19,43,48,53]      #9, 10]       , 2, 9, 10    # chans[0] - chan to use; chans[1] - chan to re-ref to !!!!!!!!! TO CHECK
        self.chansAll = [12, 42, 51, 14, 43, 53] 
        #self.numberOfChannels = 64
        
        self.size = 0.35  # size of the arrows representing left and right trials 

        self.b = []
        self.a = []


    def run(self):

        self.b, self.a = self.my_filt_design(self.bands)
        #print(self.b)

        self.marker(MARKER["experimentStart"])
        self.write('In this experiment you will be asked to imagine either a left-hand or a right-hand movement through a succession of trials.',[1,'c'],wordwrap=30,pos=[0,0.3])
        # make a better description of what's going on, even give them an example of what to expect, etc. 

        ## Set up online - Probe EEG stream
        print("Looking for EEG stream...")
        EEG = pylsl.resolve_stream('type','EEG')

        if not EEG:
            print "No EEG stream resolved, operating without it\n"
        else:
            ## Initialize EEG stream
            print "EEG stream resolved\n"
            EEGinlet = pylsl.stream_inlet(EEG[0], 1)
            EEGinlet.open_stream()
            
        ## Check stream
        checkstream = True
        if checkstream:
            self.checkstream(EEGinlet)

        ## Initialize Markers
        #self.marker("Initialize")

        ## Wait for experimenter to start experiment
        print "Press C to begin \n"
        self.waitfor('c')
        print "Starting"

        #=======================================================================
        # Training with bars
        #=======================================================================

        self.write('Please imagine moving your right hand when the arrow points to the right and imagine moving your left hand if the arrow is pointing to the left.',[1,'c'],wordwrap=30,pos=[0,0.3])

        self.write('Try to make the height of the bar on the imagery side high.',[1,'c'],wordwrap=30,pos=[0,0.3])

        
        self.run_block_bar_fb(EEGinlet,SEQBARS)
        

        self.write('Great job! Ready for the next part?',[1,'c'],wordwrap=30,pos=[0,0.3])

        self.marker(MARKER["experimentEnd"])
        
        #=======================================================================
        #
        # END OF EXPERIMENT
        #
        #=======================================================================


    def checkstream(self, EEGinlet):
        """ Runs the checks on the current stream.
        Inputs:
            self        - Self
            EEGinlet    - Data stream from LSL (EEG data stream)
        Outputs:
            None
        """

        # Get Stream Info
        streaminfo = EEGinlet.info()
        print ' '

        # Check for time correction
        self.streamtimecorrection = EEGinlet.time_correction()
        print "Time correction is: ", self.streamtimecorrection

        # Test EEG input
        testsample = pylsl.vectorf()
        testsample, timestamp = EEGinlet.pull_sample(testsample)
        print "EEG: ", testsample, timestamp
        print timestamp
        print EEGinlet.time_correction()
        print time.time()

        # Check content type
        self.streamtype = streaminfo.type()
        print "Stream Type", self.streamtype

        # Check stream name
        self.streamname = streaminfo.name()
        print "Stream Name", self.streamname

        # Check sampling rate
        self.streamsrate = streaminfo.nominal_srate()
        print "Sampling Rate", self.streamsrate

        # Check number of channels
        self.streamnchans = streaminfo.channel_count()
        print "Number of Channels", self.streamnchans

        # Check channel format
        #chanformat = streaminfo.channel_format()
        #print "Channel Format", chanformat

        print ' '


    def run_block_bar_fb(self,EEGinlet,seqT):
        # block starts    

        self.marker(MARKER["blockStart"])   

        for k in range(len(seqT)):
            if k==0:
			    self.sleep(2.5)
            print(seqT[k])
            self.marker(MARKER["beginT"])
			
            stimulus = int(seqT[k])  #choose from the previously randomly generated sequence 
            self.marker(MARKER[self.stimulus_set[stimulus]])

            # display the stimuli as left or right arrow 
            if stimulus == 0:
                self.graphics = self._engine.direct.gui.OnscreenImage.OnscreenImage(
                    image = "left.png", scale = self.size, pos = (-0.35,0,0))
                self.graphics.setTransparency(1)
            if stimulus == 1:
                self.graphics = self._engine.direct.gui.OnscreenImage.OnscreenImage(
                    image = "right.png", scale = self.size, pos = (0.35,0,0))
                self.graphics.setTransparency(1)

            # wait for a little 
            self.sleep(1.5)
            self.graphics.destroy()


            # write on the screen a cross and then imagery on top ot it 
            self.marker(MARKER["putPlus"])
            self.fixation = self.write(text = "+",
                font = self.fontFace,
                scale = .2525,
                pos = (0, 0, 0),
                fg = self.textColor,
                block = False,
                duration = 0)
            
            # wait for a little bit 
            self.sleep(1)       # gain attention for one second 

            # put the imagery cue on the cross 
            self.marker(MARKER["putImagery"])
            self.cue = self._engine.direct.gui.OnscreenText.OnscreenText(
                    text = "imagery",
                    scale = .1,
                    fg = self.textColor,
                    pos = (0, .2))
            self.cue.setTransparency(1)

            self.sleep(self.discardTime) # without this sleep, the self.cue won't appear until after the self.readBci() finishes evaluating.

            [powerR, powerL] = self.readBci(EEGinlet)
            
            #scaleFactor = 1
            #powerR = powerR/scaleFactor 
            #powerL = powerL/scaleFactor 

            self.fixation.destroy()
            self.cue.destroy()

            # features --> b = a % b + b * (a // b)

            self.plot_bars(powerR, powerL)
            
            self.marker(MARKER["endT"])

            

            self.sleep(self.wait_duration)    # this adds a jitter to the wait duration time 

            if (k+1) == len(seqT):
                self.marker(MARKER["RELAX"])
                self.write(text = self.blockEndText,
                font = self.fontFace,
                scale = self.fontSize,
                fg = self.textColor,
                duration = "c")     # until keyboard "c" is generated - as in continue 
            elif (k+1)%self.trialsInBlock==0 and (k+1)!= len(seqT):
                self.marker(MARKER["RELAX"])
                self.write(text = self.blockPauseText,
                font = self.fontFace,
                scale = self.fontSize,
                fg = self.textColor,
                duration = "c")     # until keyboard "c" is generated - as in continue 
                self.sleep(2.5)

        self.marker(MARKER["blockEnd"]) 


    def readBci(self,EEGinlet): #stores BCI data every

        # number of samples to collect 
        nsamples = self.imageryTime*self.nsamplesOrig        # Number of samples to collect (a few seconds instead of one)
        print('Number of samples to collect '+ str(nsamples))
        EEGdata = np.zeros((64, nsamples))

        # number of samples to discard 
        #nsamples_discard = self.discardTime*self.nsamplesOrig
        #temp = 0 

        
        while EEGinlet.pull_sample(timeout=0.0)[0]:
            #temp = temp+1
            pass

        startTime = time.time()
        self.marker(MARKER["beginImagery"])  # this is begin imagery 
        
        sampleIndex = 0 
        try:
            while sampleIndex<int(nsamples):
                EEGsample, timestamp = EEGinlet.pull_sample()
                if EEGsample == None:
                    print("bug!")
                    self.marker(12345)
                elif EEGsample != None:
                    EEGdata[0:64,sampleIndex] = np.array(EEGsample[0:64])                                           
                    sampleIndex = sampleIndex + 1
            
            self.marker(MARKER["endImagery"])  # this is end imagery 
        except Exception as exc:
            print("bug!")
            print exc
            print(EEGsample)
            print(timestamp)
            
        print(time.time()-startTime)
        

        # pre-process the EEG data 
        EEGdata_proc = self.preprocessEEG(EEGdata)

        # calculate the power on rihgt and left sides (electrodes), log of the normalized power
        tempVar = np.nanvar(EEGdata_proc, axis = 1)
        
        tempR = tempVar[self.chansRight]
        tempL = tempVar[self.chansLeft]

        
        powerR = np.mean(tempR)
        powerL = np.mean(tempL)
        
        print([powerL, powerR])
		

        return powerR, powerL


    def spatialFilter(self, data):
        data_filtered = np.zeros(np.shape(data))
        for ik in xrange(len(self.chansAll)):
            temp = channelLaplaceMatrix[ik]
            data_filtered[temp[0],:] = data[temp[0],:]
            for iz in xrange(len(temp)-1):
                data_filtered[temp[0],:] = data_filtered[temp[0],:]-(data[temp[iz+1],:]/4.0)

        return data_filtered



    def preprocessEEG(self, EEGdata):

        # pre-processing includes rereferecing, spatial filtering, and mu-band filtering 
		
		# spatial filtering 
        EEGdata = self.spatialFilter(EEGdata)
        # decimate to 100 Hz 
        EEGdata_dec = sig.decimate(EEGdata, self.ratDec1, axis=1, ftype='iir', zero_phase=True)  
        print(np.shape(EEGdata_dec))
        EEGdata_dec = sig.decimate(EEGdata_dec, self.ratDec, axis=1, ftype='iir', zero_phase=True)  
        print(np.shape(EEGdata_dec))

        # filter in [7 30] Hz 
        EEGdata_dec = sig.filtfilt(self.b, self.a, EEGdata_dec, axis=1, padtype='constant', method='pad', padlen= 15)
        EEGdata_dec = EEGdata_dec[:,15:3*self.srateToBe]
        print(np.shape(EEGdata_dec))
      
        return EEGdata_dec

    def plot_bars(self, powerR, powerL):
        if powerR>self.maxVar or powerL > self.maxVar:
            if powerL > powerR:
                bb = powerL // self.maxVar 
                cc = powerL % self.maxVar 
                wRectH = self.maxVar/float(bb+1)
                print(wRectH)
                remD = cc/powerL * wRectH
                barL = [None]*(int(bb)+1)
                for iijj in range(int(bb)):
                    barL[iijj] = self.rectangle(duration = 0, block = False, color = (.1,0,.9,1),rect=(-.20,-.10,(wRectH+self.distVar)*(iijj)-.5,(wRectH+self.distVar)*(iijj+1)-0.5-self.distVar))  # x1, x2, y1, y2
                    #self.sleep(0.1)
                barL[int(bb)] = self.rectangle(duration = 0, block = False, color = (.1,0,.9,1),rect=(-.20,-.10,(wRectH+self.distVar)*(bb)-.5,(wRectH+self.distVar)*(bb)+remD-0.5))  # x1, x2, y1, y2
                
                if powerR<self.maxVar:
                    barR = [None] * 1
                    remD = powerR/powerL*wRectH
                    barR[0] = self.rectangle(duration = 0, block = False, color = (.6,0,0,1), rect=(.10,.20,-.5,remD-0.5), )  # x1, x2, y1, y2
                else:
                    bb2 = powerR // self.maxVar
                    cc = powerR % self.maxVar 
                    remD = cc/powerL * wRectH
                    barR = [None] * (int(bb2)+1)
                    for iijj in range(int(bb2)):
                        barR[iijj] = self.rectangle(duration = 0, block = False, color = (.6,0,0,1),rect=(.10,.20,(wRectH+self.distVar)*(iijj)-.5,(wRectH+self.distVar)*(iijj+1)-0.5-self.distVar))  # x1, x2, y1, y2
                        #self.sleep(0.1)
                    barR[int(bb2)] = self.rectangle(duration = 0, block = False, color = (.6,0,0,1),rect=(.10,.20,(wRectH+self.distVar)*(bb2)-.5,(wRectH+self.distVar)*(bb2)+remD-0.5))  # x1, x2, y1, y2
                

            elif powerR > powerL:
                bb = powerR // self.maxVar 
                cc = powerR % self.maxVar 
                wRectH = self.maxVar/float(bb+1)
                print(wRectH)
                print(bb)
                remD = cc/powerR * wRectH
                barR = [None]*(int(bb)+1)
                for iijj in range(int(bb)):
                    barR[iijj] = self.rectangle(duration = 0, block = False, color = (.6,0,0,1),rect=(.10,.20,(wRectH+self.distVar)*(iijj)-.5,(wRectH+self.distVar)*(iijj+1)-0.5-self.distVar))  # x1, x2, y1, y2
                    #self.sleep(0.1)
                barR[int(bb)] = self.rectangle(duration = 0, block = False, color = (.6,0,0,1),rect=(.10,.20,(wRectH+self.distVar)*(bb)-.5,(wRectH+self.distVar)*(bb)+remD-0.5))  # x1, x2, y1, y2
                
                if powerL<self.maxVar:
                    barL = [None]*1
                    remD = powerL/powerR*wRectH
                    barL[0] = self.rectangle(duration = 0, block = False, color = (.1,0,.9,1), rect=(-.20,-.10,-.5,remD-0.5), )  # x1, x2, y1, y2
                else:
                    bb2 = powerL // self.maxVar
                    cc = powerL % self.maxVar 
                    remD = cc/powerR * wRectH
                    barL = [None]*(int(bb2)+1)
                    for iijj in range(int(bb2)):
                        barL[iijj] = self.rectangle(duration = 0, block = False, color = (.1,0,.9,1),rect=(-.20,-.10,(wRectH+self.distVar)*(iijj)-.5,(wRectH+self.distVar)*(iijj+1)-0.5-self.distVar))  # x1, x2, y1, y2
                        #self.sleep(0.1)
                    barL[int(bb2)] = self.rectangle(duration = 0, block = False, color = (.1,0,.9,1),rect=(-.20,-.10,(wRectH+self.distVar)*(bb2)-.5,(wRectH+self.distVar)*(bb2)+remD-0.5))  # x1, x2, y1, y2
        else:
            barR = [None]*1
            barL = [None]*1
            barL[0] = self.rectangle(duration = 0, block = False, color = (.1,0,.9,1),rect=(-.20,-.10,-.5,powerL-0.5))  # x1, x2, y1, y2
            barR[0] = self.rectangle(duration = 0, block = False, color = (.6,0,0,1), rect=(.10,.20,-.5,powerR-0.5), )  # x1, x2, y1, y2    
            


        self.sleep(3.5)

        for iijj in range(len(barL)):
            barL[iijj].destroy()
        for iijj in range(len(barR)):
            barR[iijj].destroy()

    def my_filt_design(self, bands):

        srate = 100
        N = 3
        print(bands)
        Wn = self.bands/(float(self.srateToBe/2))
        b,a = sig.iirfilter(N, Wn, rp=None, rs=None, btype='band', analog=False, ftype='butter', output='ba')
        return b, a


