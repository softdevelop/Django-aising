#Copyright 2013 Richard Giuly
#All rights reserved

import amusic1
import sys
import random
import os
import operator
import numpy
import waveutil
import songeval
from threading import Thread
from time import sleep, gmtime, strftime
import time


moduloForChords = 12
#moduloForChords = 6


trackIndex = 0
typeIndex = 1
pitchIndex = 2
startTimeIndex = 3
channelIndex = 6

printOn = 1




#from numpy import *

midiSourceFolder = "midi_source"

def weightedChoice(choices, weights):

    #print "choices", choices
    #print "weights", weights

    total = float(0)
    #print "weights", weights
    for w in weights:
        total += float(w)

    # if weights are all zero so just pick something randomly
    if total == 0:
        return random.choice(choices)

    indexes = range(len(choices))

    random.shuffle(indexes)

    while(True):
        for i in indexes:
            choice = choices[i]
            probability = float(weights[i]) / float(total)
            #print probability
            #print "random", random.random()
            if random.random() < probability:
                return choice



def songToNotes(song, limit):

    print "limiting to %d notes" % limit

    events = song.events

    notes = []
    #intervals = []
    count = 0
    lastStartTime = 0

    # make list of notes
    for event in sorted(events, key=operator.itemgetter(trackIndex, startTimeIndex)):
        if event[typeIndex] == 'note':
            if printOn: print "-----------------------------------"
            if printOn: print "event", event
            intervalBeforeThisNote = float(int(1000 * (event[startTimeIndex] - lastStartTime))) / 1000.0
            if printOn: print "intervalBeforeThisNote", intervalBeforeThisNote
            #intervals.append(intervalBeforeThisNote)
            lastStartTime = event[startTimeIndex]
            #print event[startTimeIndex]
            notes.append(event[pitchIndex])

            count += 1
            if count > limit:
                break

    return notes



def songToChords(song, limit):

    chords = []
    lastStartTime = -1
    events = song.events
    count = 0
    for event in sorted(events, key=operator.itemgetter(trackIndex, startTimeIndex)):
        if event[typeIndex] == 'note':

            # create new set if the time associated with the current note is not the same as the last
            if event[startTimeIndex] != lastStartTime:
                chords.append(set())

            # using % 10 (or whatever) does something that could be useful
            pitch = (event[pitchIndex] % moduloForChords) + 60

            chords[-1].add(pitch)

            #print "chords", chords

            lastStartTime = event[startTimeIndex]

            count += 1
            if count > limit:
                break

    frozenChords = map(frozenset, chords)

    return frozenChords


def songToIDs(song, limit):

    chords = songToChords(song, limit)
    chordsToIDs = {}
    #mapped = {}
    IDsToChords = {}
    IDs = []
    id = -1

    # map chords to numbers
    for chord in chords:
        if chord not in chordsToIDs:
            # add new entry in map
            id += 1
            chordsToIDs[chord] = id
            IDsToChords[id] = chord
        else:
            id = chordsToIDs[chord]

        IDs.append(id)

    return (IDs, IDsToChords)


def songToBitChords(song, limit):

    chords = songToChords(song, limit)

    bitChords = []

    for chord in chords:
        bitChord = []
        for i in range(moduloForChords):
            bitChord.append(0)
        for note in chord:
            bitChord[note % moduloForChords] = 1
        bitChords.append(bitChord)

    return bitChords
    #note: for a future system, prediction from chord could just be one note



def createProbabilitySong(db, songName, options, outputTempo):

    numNotes = 100


    db.newPopulation('temp')
    db.setPopulation('temp')

    foundMIDISource = False


    #sizeOnEachSide = 3
    inputSize = 5


    inputs = []
    outputs = []

    intervalInputs = []
    intervalOutputs = []

    db.setPopulation('p1')
    
    newSong = db.getCurrentPopulation().Song(songName)
    newSong.clear()
    newSong.addTempo(60000000/outputTempo, 0)
    t = 60000.0/120.0/newSong.ppq

    lengthOfPrimer = inputSize
    notes = [] #todo: call this predictionOutputs
    harmonyNotes = []
    intervals = []

    for i in range(100):
        notes.append(random.randint(50, 80))


    if printOn: print "generated notes", notes
    if 0:
        if printOn: print "generated intervals", intervals
    
    del notes[0:lengthOfPrimer]
    if 0:
        del intervals[0:lengthOfPrimer]
    
    duration = 0.2
    for i in range(len(notes)):
        startTime = float(i) * (newSong.ppq / 1000.0)
        newSong.addNote(0, notes[i], startTime, duration*4/t, 0x40)


    return newSong





# generates list of events for every time interval
def sampleSong(db, midiFilename, samplesPerQuarterNote, channel):

    db.newPopulation('temp')
    db.setPopulation('temp')

    filename = os.path.join(midiFilename)

    song = db.getCurrentPopulation().Song("testsample")
    song.fromFile(str(filename))
    song.toDB()

    # put events in order
    rawEvents = sorted(song.events,key=operator.itemgetter(trackIndex, channelIndex, startTimeIndex))

    notesOnChannel = {}

    events = []


    # set channel, use one that has notes if the selected one doesn't have any
    if channel != None:

        # count notes on each channel
        for e in rawEvents:
            #if e[channelIndex] != 10:
            if e[typeIndex] == 'note':
                if e[channelIndex] in notesOnChannel:
                    notesOnChannel[e[channelIndex]] += 1
                else:
                    notesOnChannel[e[channelIndex]] = 0
    
        if not(channel in notesOnChannel):
            # if no events found on specified channel, use another one with notes
            print "no events of channel %d, using others" % channel
            for key in notesOnChannel:
                if notesOnChannel > 0:
                    channel = key
                    break

    print "using channel", channel

    # use events from one channel
    for e in rawEvents:
        #if channel == None or e[channelIndex] == channel:
        if channel == None or e[channelIndex] == channel:
            if e[typeIndex] == 'note':
                events.append(e)



    # find max start time
    maxTime = 0
    for event in events:
        time = event[startTimeIndex]
        if time > maxTime:
            maxTime = time

    sampleRateFactor = samplesPerQuarterNote * 1000.0 / song.ppq

    numSamples = int(sampleRateFactor * maxTime) + 2

    if printOn: print "number of samples:", numSamples

    samples = -numpy.ones(numSamples)
    grid = numpy.ones(numSamples)
    gridIndex = 0

    while gridIndex < len(grid):
        for quarterNoteCount in range(4):
            for value in (0, 1):
                for fractionalCount in range(samplesPerQuarterNote):
                    #print "value", value
                    if gridIndex >= len(grid):
                        break
                    grid[gridIndex] = value
                    #gridCount = (quarterNoteCount * samplesPerQuarterNote) + fractionalCount
                    #grid[gridIndex] = gridCount
                    gridIndex += 1


    totalError = 0.0
    #numNotes = 0

    print "-----------------------------------------------------------"

    for event in events:

        print "start time:", event[startTimeIndex]

        if event[typeIndex] == 'note':
            print "note", event[pitchIndex]
            #print "index=%d pitch=%d" % (index, event[pitchIndex])
            index = round(event[startTimeIndex] * float(sampleRateFactor))
            original = event[startTimeIndex] * float(sampleRateFactor)
            #quantized = round(event[startTimeIndex] * float(sampleRateFactor))
            if printOn: print "quantization from sampling", original, index

            totalError += abs(original-index)
            #numNotes += 1
            
            samples[index] = event[pitchIndex]

            #print "quantization error:", totalError

    db.setPopulation('p1')

    print "grid", grid

    return samples, grid




def midiFromSamples(samples, rate, outputTempo=120):

    song = db.getCurrentPopulation().Song("midifromsamplestest")
    song.clear()
    song.addTempo(60000000/outputTempo, 0)

    startTime = 0

    for i in range(len(samples)):
        sample = int(samples[i])
        #print "test"
        if sample != -1:
            startTime = float(i) * float(song.ppq) / (1000.0 * float(rate))
            #print "test"
            #song.addNote(0, sample, i * (0.003 / float(rate)), 0.2, 0x40)
            song.addNote(0, sample, startTime, 0.2, 0x40)

    patch = 5
    song.toFile("midifromsamplestest.mid", patch)
    print os.path.join(os.getcwd(), "midifromsamplestest.mid")



def countMIDIFiles(options):

    count = 0
    for sourceSongName in options:
        filename = os.path.join(midiSourceFolder, sourceSongName + ".mid")
        if os.path.isfile(filename):
            print "using file:", filename
            count += 1

    return count



def createProbabilitySongUsingSamples(db, songName, midiFilenames, outputTempo):

    db.setPopulation('p1')

    newSong = db.getCurrentPopulation().Song(songName)
    newSong.clear()
    newSong.addTempo(60000000/outputTempo,0)
    t = 60000.0/120.0/newSong.ppq

    if 'Use_3_Time' in midiFilenames:
        rate = 6
    else:
        rate = 4


    numTracks = 1
    for count in range(numTracks):

        (outputSamples, harmonyOutputSamples) = createProbabilitySongUsingSamples1(db, songName, midiFilenames, rate, outputTempo)
        if outputSamples == None:
            print "no inputs error"
            return None
    
        if printOn: print "generated samples", outputSamples, harmonyOutputSamples
        
        for i in range(len(outputSamples)):
            #startTime = i * 0.1 / float(rate)
            startTime = float(i) * float(newSong.ppq) / (1000.0 * float(rate))
            pitch = outputSamples[i]
            if pitch != -1:
                newSong.addNote(0, pitch, startTime, 0.2, 0x40)
            pitch = harmonyOutputSamples[i]
            if pitch != -1:
                newSong.addNote(0, pitch, startTime, 0.2, 0x40)



    return newSong



#newSong.synth("songprobability.mp3")
#newSong.toDB()


def saveSong(db, song):

    currentTimeString = strftime("%Y-%m-%d_%H-%M-%S", gmtime())

    print "saving song"
    db.newPopulation('permanent')
    population = db.getPopulation('permanent')
    oldPopulation = song.population
    oldTitle = song.title
    song.population = population
    song.title = "s" + currentTimeString
    song.toDB()
    song.synth(tempFilename="save_song_temp_file")
    song.population = oldPopulation
    print "finished saving song"



def runCreateProbabilitySong(options, name='outputsong'):

    db = amusic1.getDatabaseObject()


    #outputTempo = 200

    if 'Rythm' in options:
        outputTempo = 120
        if 'Fast_Tempo' in options:
            outputTempo = int(float(outputTempo) * 1.8)
        newSong = createProbabilitySongUsingSamples(db, name, options, outputTempo)
    else:
        outputTempo = 220
        if 'Fast_Tempo' in options:
            outputTempo = int(float(outputTempo) * 1.8)
        newSong = createProbabilitySong(db, name, options, outputTempo)


    if 'Two_Part_Tune_Maker' in options:
        notes = numpy.array((-1, 0, 2, 4, 7, 9)) + 50
        newSong = songeval.createRepetitiveBassLine((random.choice(notes), random.choice(notes), random.choice(notes), random.choice(notes)))

    if newSong == None:
        print "no midi file inputs were found"
        return "error"

    notes = songToNotes(newSong, 1000)

    patch = None

    if 'General_MIDI_Instrument_Number' in options:
        try:
            patch = int(options['General_MIDI_Instrument_Number'])
            print "patch from the web interface option:", patch
        except:
            print "value not readable"
            patch = 0

    if patch < 1 or patch > 128:
        patch = 1

    # adjusts from 1 based (for humans) to 0 based (for the computer)
    patch -= 1

    newSong.toDB()
    print "synthesizing"
    
    print "patch after checking sanity:", patch

    newSong.channelForTrack[0] = 0
    newSong.patchForTrack[0] = patch
    newSong.synth("outputsong.mp3")

    if 'Experimental_Feature_Voice_Synth' in options:
        words = options['Experimental_Feature_Voice_Synth'].split()
        if len(words) > 0:
            waveutil.addVoice("temp.wav", "temp.wav", words, notes, outputTempo)

    #waveutil.addVoice("temp.wav", "withvoice.wav", "hello how are you".split(), notes, outputTempo)
    #if 0:
    #    waveutil.addVoice("temp.wav", "withvoice.wav", waveutil.testText.split(), notes, outputTempo)

    #thread = Thread(target=saveSong, args=(db, newSong))
    #thread.start()
    saveSong(db, newSong)

    return "success"


if __name__ == '__main__':


    if 1:
        #runCreateProbabilitySong({'EspanjaPrelude':'on', 'Rythm':'on'})
        runCreateProbabilitySong({'EspanjaPrelude':'on'})
        #runCreateProbabilitySong({'daft_punk_get_lucky_feat_pharrell_williams':'on', 'channel_daft_punk_get_lucky_feat_pharrell_williams':'0', 'Rythm':'on'})

    # sample song and write it to midi file
    if 0:
        #filename = "daft_punk_get_lucky_feat_pharrell_williams.mid"
        #filename = "rgiuly_064.mid"
        filename = "bach12a.mid"
        perQuarterNote = 6
        db = amusic1.initialize()
        #samples = sampleSong(db, "EspanjaPrelude.mid", perQuarterNote, 0)
        channel = None
        samples = sampleSong(db, os.path.join("midi_source", filename), perQuarterNote, channel)
        print "samples"
        for s in samples:
            print s
        midiFromSamples(samples, perQuarterNote, outputTempo=120)

    if 0:
        folder = "midi_source"
        for filename in os.listdir(folder):
            if filename.endswith(".mid"):
                print filename
                name = os.path.splitext(filename)[0]
                try:
                    runCreateProbabilitySong({name:'on'}, name=filename)
                except:
                    print "error in lear.py at __main__" 



    if 0:
        thread = Thread(target=threaded_function, args=(1, ))
        thread.start()
        #thread.join()

        thread = Thread(target=threaded_function, args=(2, ))
        thread.start()
        #thread.join()



