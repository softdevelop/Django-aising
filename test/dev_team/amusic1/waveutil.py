#import numpy
#import wave
#
#w1 = wave.open("i:\\Dropbox\\temp\\test1.wav", 'r')
#w2 = wave.open("i:\\Dropbox\\temp\\test2.wav", 'r')
#print "width", w1.getsampwidth()
#f1 = w1.readframes(2000)
#f2 = w2.readframes(2000)
#a1 = numpy.zeros(len(f1))
#a2 = numpy.zeros(len(f1))
#for i in xrange(len(f1)):
#    a1[i] = ord(f1[i])
#    #print a1[i]
#    a2[i] = ord(f2[i])
#
#print a1
#print a2
#
#b = a1 + a2
#
##bchars = ""
##for i in xrange(len(f1)):
##    value = b[i]
##    bchars += chr(value)

import scipy
import scipy.io
import scipy.io.wavfile
import scipy.signal
import os
import numpy
import math
from matplotlib.mlab import find
#file

def testESpeak():

    os.system('espeak -w i:\\Dropbox\\temp\\test2.wav "hello how are you"')
    os.system('espeak -w i:\\Dropbox\\temp\\test3.wav "i am fine thank you"')
    
    a = scipy.io.wavfile.read("i:\\Dropbox\\temp\\test2.wav")
    b = scipy.io.wavfile.read("i:\\Dropbox\\temp\\test3.wav")
    
    print a[1]
    print b[1]
    
    c = a[1]
    d = b[1]
    minimum = min(len(c), len(d))
    e = c[0:minimum] + d[0:minimum]
    #e = c[0:minimum]
    scipy.io.wavfile.write("i:\\Dropbox\\temp\\test_out.wav", a[0], e)


#Eng Eder de Souza 01/12/2011
#ederwander
def calculatePitch_other(signal):

    RATE = 44100/2
    crossing = [math.copysign(1.0, s) for s in signal]
    index = find(numpy.diff(crossing));
    f0 = round(len(index) * RATE /(2*numpy.prod(len(signal))))
    return f0;


def calculatePitch(indata):

    chunk = len(indata)
    RATE = 44100/2

    # Take the fft and square each value
    fftData=abs(numpy.fft.rfft(indata))**2
    # find the maximum
    which = fftData[1:].argmax() + 1

    #thefreq = (which)*RATE/chunk
    #return thefreq

    # use quadratic interpolation around the max
    if which != len(fftData)-1:
        y0,y1,y2 = numpy.log(fftData[which-1:which+2:])
        x1 = (y2 - y0) * .5 / (2 * y1 - y2 - y0)
        # find the frequency and output it
        thefreq = (which+x1)*RATE/chunk
        return thefreq
    else:
        thefreq = which*RATE/chunk
        return thefreq

def tune_old(input, f):

    output = numpy.zeros((0))

    chunkSize = 5000

    last = f

    for chunkIndex in xrange(len(input)/chunkSize):

        #print "chunkIndex", chunkIndex

        inputChunk = input[chunkIndex*chunkSize : (chunkIndex+1)*chunkSize]

        calculatedPitch = calculatePitch(inputChunk)

        if calculatedPitch > 900:
            calculatedPitch = calculatedPitch / 2

        if calculatedPitch < 390:
            calculatedPitch = calculatedPitch * 2

        #calculatedPitch = 440


        if numpy.isnan(calculatedPitch):
            print "warning: calculated pitch is nan"
            #calculatedPitch = f
            calculatedPitch = last

        if calculatedPitch == 0:
            print "warning: calculated pitch is 0"
            #calculatedPitch = f
            calculatedPitch = last

        last = calculatedPitch

        factor = 1 * calculatedPitch / f
        #factor = 2 #normal
        print "f", f
        print "calculatedPitch", calculatedPitch
        print "factor", factor
        print "len(inputChunk)", len(inputChunk)
        outputChunk = numpy.zeros(factor*len(inputChunk))
        #voice = scipy.signal.resample(numpy.array([1]), 2*len(rawVoice))
        for q in xrange(len(outputChunk)):
            outputChunk[q] = inputChunk[math.floor(q/factor)]

        #todo: this is probably not efficient
        output = numpy.concatenate((output, outputChunk))

    return output



def addVoice(inFilename, outFilename, words, notes, outputTempo):
    # open wave music output file are make it an array
    # for each word in text, have the speech reader generate a temporary wave file and put the wave file into the array (need to do a "+=" kind of operation)
    # output the modified wave file

    # read background
    rate, backgroundStereo = scipy.io.wavfile.read(inFilename)
    background = backgroundStereo[:, 0]
    print rate

    #notes = numpy.array([5, 3, 1, 3, 5, 5, 5, 3, 3, 3, 5, 8, 8]) + 60
    #shortness = numpy.array([20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 80, 80, 200])

    # read words and place them on background

    currentWordIndex = 0

    for i in xrange(len(notes)):

        #notes[i] = 58 

        if notes[i] == -1:
            continue

        # stop reading once you run out of words
        if currentWordIndex >= len(words) - 1:
            break

        currentWordIndex += 1

        #print words[i]

        pitch = 99
        #wordsPerMinute = 80
        wordsPerMinute = 160
        #wordsPerMinute = shortness[i]
        volume = 100

        print "synthesizing word"
        os.system('espeak -a %d -p %d -s %d -w temp_voice.wav "%s"' % (volume, pitch, wordsPerMinute, words[currentWordIndex%len(words)]))
        print "finished synthesizing word"
        rate, rawVoice = scipy.io.wavfile.read("temp_voice.wav")

        n = notes[i]
        f = pow(2,(n-69.0)/12.0) * 440.0

        # replace with sin wave
        if 0:
            for r in xrange(len(rawVoice)):
                rawVoice[r] = 100 * 256 * math.sin(float(r) / 30)

        print "currentWordIndex", currentWordIndex
        print "number of notes:", len(notes), "note value", n
        x = len(rawVoice)
        #print "x/2", x/2
        #calculatedPitch = calculatePitch(rawVoice)
        D = 293.665
        A = 440.0
        calculatedPitch = D * 2
        print "calculated pitch:", calculatedPitch
        print "desired pitch:", f

        #voice = scipy.signal.resample(rawVoice, 2*len(rawVoice))
        #factor = 1 * (i/3)
        factor = 1 * calculatedPitch / f
        #factor = 2 #normal
        voice = numpy.zeros(factor*len(rawVoice))
        #voice = scipy.signal.resample(numpy.array([1]), 2*len(rawVoice))
        for q in xrange(len(voice)):
            voice[q] = rawVoice[math.floor(q/factor)]
            #voice[q] = rawVoice[q]
        #    voice[q] = 0
        #voice[0] = 0

        #voice = tune(rawVoice, f)

        #print "adjusted pitch, calculated", calculatePitch(voice)


        sum = background

        beatTimeInSeconds = 60.0 / outputTempo

        step = beatTimeInSeconds * float(rate) * 2.0
        #step = 0.2 * float(rate)
        #offset = int(2.5 * float(rate))
        offset = 0
        #offset = step

        if offset+i*step >= len(sum) or offset+i*step+len(voice) >= len(sum):
            print "went past end of file while writing in voice information"
            break

        sum[offset+i*step:offset+i*step+len(voice)] += voice
        #istep = int(i*step)

        #print "i", i
        #print "step", step
        #print "offset", offset

        #for j in xrange(offset+istep, offset+istep+len(voice)):
            #print j
            #print len(voice)
            #print "len sum", len(sum)
            #print "j", j
            #print "len voice", len(voice)
            #print "j-(offset+istep)", j-(offset+istep)
            #sum[j] += voice[j-(offset+istep)]

#    if len(background) > len(voice):
#        #sum = numpy.zeros(len(background))
#        print "background longer"
#        sum = background
#        step = 2.0 * float(rate)
#        for i in xrange(10):
#            sum[i*step:i*step+len(voice)] += voice
#    else:
#        #sum = numpy.zeros(len(voice))
#        print "voice longer"
#        sum = voice
#        sum[0:len(background)] += background

    print outFilename
    scipy.io.wavfile.write(outFilename, rate*2, sum)


testText = "Once upon a midnight dreary, while I pondered, weak and weary,Over many a quaint and curious volume of forgotten lore While I nodded, nearly napping, suddenly there came a tapping,As of some one gently rapping rapping at my chamber door."


if __name__ == '__main__':

    testNotes = numpy.array([ -1,  -1,  57,  -1,  64,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
      -1,  -1,  62,  62,  -1,  60,  -1,  62,  -1,  64,  -1,  65,  -1,  67,  -1,
      64,  -1,  65,  -1,  64,  62,  62,  -1,  -1,  -1,  60,  -1,  -1,  -1,  58,
      -1,  -1,  -1,  45,  -1,  52,  -1,  57,  -1,  61,  -1,  64,  -1,  69,  -1,
      73,  -1,  61,  -1,  64,  -1,  69,  -1,  73,  -1,  76,  -1,  81,  -1,  76,
      -1,  73,  -1,  69,  -1,  64,  -1,  61,  -1,  69,  -1,  64,  -1,  61,  -1,
      57,  -1,  52,  -1,  49,  -1,  45,  -1,  57,  -1,  64,  -1,  -1,  -1,  -1,
      -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  62,  62,  -1,  60,  -1,  62,  -1,
      64,  -1,  65,  -1,  67,  -1,  64,  -1,  65,  -1,  64,  62,  62,  -1,  -1,
      -1,  60,  -1,  -1,  -1,  58,  -1,  -1,  -1,  57,  -1,  58,  -1,  60,  -1,
      62,  -1,  65,  -1,  -1,  62,  62,  -1,  -1,  -1,  60,  -1,  -1,  -1,  58,
      -1,  -1,  -1,  57,  -1,  58,  -1,  60,  -1,  62,  -1,  64,  -1,  67,  -1,
      65,  62,  62,  -1,  60,  -1,  58,  -1,  62,  -1,  61,  -1,  45,  61,  -1,
      69,  52,  61,  -1,  69,  57,  61,  -1,  69,  45,  62,  -1,  67,  52,  62,
      -1,  67,  58,  62,  -1,  67,  45,  61,  -1,  69,  52,  61,  -1,  69,  57,
      61,  -1,  69,  45,  62,  -1,  69,  52,  62,  -1,  67,  58,  62,  -1,  64,
      45,  61,  -1,  69,  52,  61,  -1,  69,  57,  61,  -1,  69,  41,  57,  -1,
      65,  48,  57,  -1,  65,  57,  57,  -1,  65,  48,  60,  -1,  64,  55,  60,
      -1,  64,  60,  60,  -1,  64,  55,  58,  -1,  62,  57,  58,  -1,  62,  58,
      58,  -1,  62,  45,  61,  -1,  69,  52,  61,  -1,  69,  57,  61,  -1,  69,
      45,  62,  -1,  67,  52,  62,  -1,  67,  58,  62,  -1,  67,  45,  61,  -1,
      69,  52,  61,  -1,  69,  57,  61,  -1,  69,  45,  62,  -1,  67,  52,  62,
      -1,  67,  58,  62,  -1,  67,  45,  -1,  57,  -1,  59,  -1,  61,  -1,  62,
      -1,  64,  -1,  65,  -1,  -1,  64,  64,  -1,  62,  -1,  60,  -1,  62,  -1,
      64,  -1,  65,  -1,  67,  -1,  64,  -1,  65,  -1,  64,  62,  62,  -1,  -1,
      -1,  60,  -1,  -1,  -1,  58,  -1,  -1,  -1,  57,  -1,  59,  -1,  61,  -1,
      62,  -1,  64,  -1,  65,  -1,  67,  -1,  69,  70,  70,  -1,  -1,  -1,  69,
      -1,  67,  -1,  69,  -1,  -1,  -1,  69,  -1,  67,  -1,  70,  -1,  69,  65,
      65,  -1,  63,  -1,  62,  -1,  64,  -1,  60,  -1,  58,  -1,  45,  61,  -1,
      69,  52,  61,  -1,  69,  57,  61,  -1,  69,  45,  62,  -1,  67,  52,  62,
      -1,  67,  58,  62,  -1,  67,  45,  61,  -1,  69,  52,  61,  -1,  69,  57,
      61,  -1,  69,  45,  62,  -1,  69,  52,  62,  -1,  67,  58,  62,  -1,  64,
      45,  61,  -1,  69,  52,  61,  -1,  69,  57,  61,  -1,  69,  41,  57,  -1,
      65,  48,  57,  -1,  65,  57,  57,  -1,  65,  48,  60,  -1,  64,  55,  60,
      -1,  64,  60,  60,  -1,  64,  55,  58,  -1,  62,  57,  58,  -1,  62,  58,
      58,  -1,  62,  45,  -1,  -1,  -1,  52,  -1,  -1,  -1,  57,  -1,  -1,  -1,
      50,  52,  -1,  53,  55,  57,  -1,  58,  60,  58,  -1,  57,  45,  -1,  -1,
      -1,  52,  -1,  -1,  -1,  57,  -1,  -1,  -1,  50,  52,  -1,  53,  55,  57,
      -1,  58,  60,  58,  -1,  57,  56,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
      -1,  -1,  -1,  58,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
      -1,  -1,  60,  -1,  62,  -1,  65,  -1,  62,  -1,  60,  60,  60,  -1,  58,
      -1,  53,  -1,  58,  -1,  57,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  56,  -1,
      53,  -1,  52,  -1,  50,  -1,  45,  -1,  52,  -1,  57,  -1,  61,  -1,  64,
      -1,  69,  -1,  73,  -1,  61,  -1,  64,  -1,  69,  -1,  73,  -1,  76,  -1,
      81,  -1,  61,  -1,  64,  -1,  69,  -1,  73,  -1,  76,  -1,  81,  -1,  73,
      -1,  76,  -1,  81,  -1,  85,  -1,  88,  -1,  85,  -1])

    testNotes = testNotes[0:100]
    
    #testESpeak()
    
    #addVoice("i:\\temp\\outputsong.wav", "i:\\temp\\outputsongwithvoice.wav", "mare ree had a lit tul lamb lit tul lamb lit tul lamb mare ree had a lit tul lamb lit tul lamb lit tul lamb mare ree had a lit tul lamb lit tul lamb lit tul lamb mare ree had a lit tul lamb lit tul lamb lit tul lamb mare ree had a lit tul lamb lit tul lamb lit tul lamb mare ree had a lit tul lamb lit tul lamb lit tul lamb mare ree had a lit tul lamb lit tul lamb lit tul lamb ")
    
    testWords = testText.split()
    addVoice("i:\\temp\\outputsong.wav", "i:\\temp\\outputsongwithvoice.wav", testWords, testNotes)
    
    #print scipy.signal.resample(numpy.array([1, 2, 3, 4, 5]), 10)


