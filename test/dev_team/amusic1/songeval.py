import time
import random
import sys
from amusic1 import *
from boto.mturk.qualification import PercentAssignmentsApprovedRequirement
from boto.mturk.qualification import NumberHitsApprovedRequirement
from boto.mturk.qualification import Qualifications
from learn import *
import numpy
import pickle
import traceback

numAssignmentsPerHIT = 4

# use these to control what runs
# these could be command line options
doInitPopulationRandomly = 0
doRestartPopulationEval = 0
doCollect = 0
deleteEnabled = 1
forceAllSelectionsArtificiallyForTesting = 0


# population size
sizeDuringReproduction = 10
sizeAfterReproduction = 7
#sizeOfSubset = 3# standard
sizeOfSubset = 6
#sizeDuringReproduction = 3
#sizeAfterReproduction = 2
#sizeOfSubset = 1


nextNumberValue = 0


db = getDatabaseObject()

#numSongs = 3
#songs = []
#ratings = {}


def filterListOfPairs_old(rawListOfPairs):

    alreadyUsed = {}
    listOfPairs = []

    # eliminate ones that are (1) already there, (2) just reversed versions of one already there, or (3) the same twice
    for item in rawListOfPairs:

        skip = False

        if (item[0] == item[1]):
            skip = True

        if ((item[0], item[1]) in alreadyUsed):
            skip = True

        alreadyUsed[(item[0], item[1])] = True
        alreadyUsed[(item[1], item[0])] = True

        if not(skip): 
            print "added", item
            listOfPairs.append(item)
        else:
            print "skipped", item

    return listOfPairs



def submitComparisons(population):
    #print "mturkLayoutID", population.amusic.conf['mturkLayoutID']

    rawListOfPairs = []

    if not population.amusic.conf['mturkLayoutID']:
        print "LayoutID not set"
        return
    l = [i[0] for i in population.amusic.engine.execute('SELECT title FROM song WHERE population="%s";'%(population.title)).fetchall()]
    print "list of songs", l
    tempList = list(l)
    subset = []
    for count in range(sizeOfSubset):
        item = tempList.pop(random.randint(0, len(tempList)-1))
        subset.append(item)
    print "subset", subset
    for d,i in enumerate(l):
        print 'Song %d/%d (%s)'%(d+1,len(l),i)
        s = Song(population,i)
        s.fromDB()
        s.synth(i+'.mp3' if i.find('.')==-1 else i[:i.find('.')]+'.mp3',upload=True,generateMP3=True)
    print "Creating HITs..."
    print "host:", population.amusic.mtc.host
    s = "http://%s.s3.amazonaws.com/tracks/" % (population.amusic.conf['bucket'])
    n=1

    #for d,i in enumerate(l):
    for i in l:
        for j in subset:
            rawListOfPairs.append([i, j])

    #listOfPairs = filterListOfPairs(rawListOfPairs)
    listOfPairs = rawListOfPairs

    # submit items to mechanical turk
    for i, j in listOfPairs:
        f1 = i+'.mp3' if i.find('.')==-1 else i[:i.find('.')]+'.mp3'
        f2 = j+'.mp3' if j.find('.')==-1 else j[:j.find('.')]+'.mp3'
        #print "\tHIT %d/%d (%s,%s)" % (n,len(l)*(len(l)-1)/2,f1,f2)
        print "\tHIT %d (%s, %s)" % (n, f1, f2)
        params = LayoutParameters()
        params.add(LayoutParameter('file1',s+f1))
        params.add(LayoutParameter('file2',s+f2))
        #print population.amusic.conf['hitRewardPerAssignment']
        #sys.exit()
        #quals = quals = Qualifications();
        quals = Qualifications();
        quals.add(PercentAssignmentsApprovedRequirement("GreaterThanOrEqualTo", "97"))
        quals.add(NumberHitsApprovedRequirement("GreaterThanOrEqualTo", "100"))
        population.amusic.mtc.create_hit(hit_layout=population.amusic.conf['mturkLayoutID'],
                                         layout_params=params,
                                         reward=0.01,
                                         title=population.amusic.conf['hitTitle'],
                                         description=population.amusic.conf['hitDescription'],
                                         keywords=population.amusic.conf['hitKeywords'],
                                         duration=timedelta(minutes=3),
                                         lifetime=timedelta(minutes=300),
                                         qualifications=quals,
                                         max_assignments=numAssignmentsPerHIT)
        n+=1

    print "raw list of pairs has %d items" % len(rawListOfPairs)
    print "cleaned list of pairs has %d items" % len(listOfPairs)
    return listOfPairs



def createRandomSongs(numSongs):

    for i in range(numSongs):

        songName = 's%d' % i
        
        
        if random.randint(0, 1) == 0:
            song = db.getCurrentPopulation().Song(songName)
            song.regularRepeat(8, 0.3)
        else:
            song = createProbabilitySong(db, songName)

        song.toDB()
        del song
        
        song = db.getCurrentPopulation().Song(songName)
        song.fromDB()
        song.synth(songName + ".mp3")



def createRepetitiveBassLines(populationName, numBasslines=1):

    #db.setPopulation(populationName)

    notes = numpy.array((-1, 0, 2, 4, 5, 7, 9)) + 50 + random.randint(0, 5)

    songs = []

    for n0 in notes:
        for n1 in notes:
            for n2 in notes:
                for n3 in notes:
                    criticalNotes = n0, n1, n2, n3

                    repeat = False
                    # skip sequences with repeats
                    for i in range(len(criticalNotes)-1):
                        if criticalNotes[i] == criticalNotes[i+1]:
                            repeat = True

                    if not(repeat):
                        songs.append(createRepetitiveBassLine(criticalNotes))

    #todo: move out of this function
    #for song in songs:
    #    song.toDB()
    #    song.synth(song.title + ".mp3")
    for i in range(numBasslines):
        # select song randomly and remove from list
        song = songs.pop(random.randint(0, len(songs)))
        db.newPopulation(populationName)
        song.population = db.getPopulation(populationName)
        song.toDB()
        #song.synth(song.title + ".mp3")
        song.synth(generateMP3=True)



def createRepetitiveBassLine(criticalNotes):

    db.engine.execute('USE amusic')

    songName = 's'
    for note in criticalNotes:
        songName += str(note)
        songName += "_"

    notes = []

    #db.setPopulation(populationName)

    db.setPopulation('p1')
    song = db.getCurrentPopulation().Song(songName)
    song.clear()
    outputTempo = 80
    song.addTempo(60000000/outputTempo, 0)
    duration = (song.ppq / 1000.0)

    #song.patchForTrack[0] = random.randint(0, 128)
    song.patchForTrack[0] = 1
    #song.patchForTrack[1] = 0
    #song.channelForTrack[0] = 0
    #song.channelForTrack[1] = 0

    for note in criticalNotes:
        for j in range(4):
            notes.append(note)

    factor = 2

    melody = []
    for i in range(factor * len(notes) * 2):
        melody.append(random.choice(numpy.array((-1, 0, 2, 4, 7, 9))) + 50 + 12)

    # bass notes
    for i in range(factor * len(notes)):
        startTime = float(i) * (song.ppq / 1000.0)
        pitch = notes[i%len(notes)]
        song.addNote(0, pitch, startTime, 0.99*duration, 0x40)

    if 0:
        # bass drum
        for i in range(factor * len(notes)/2):
            startTime = (song.ppq / 1000.0) + float(i) * (song.ppq / 1000.0) * 2
            song.addNote(1, 36, startTime, 0.99*duration, 0x40)

    # melody

    if random.randint(0, 1) == 0:
        leaveRests = True
    else:
        leaveRests = False
    #leaveRests = True


    for i in range(factor * len(notes) * 2 + 1):

        # generate new next note
        if leaveRests:
            if random.randint(0, 5) == 0:
                nextIsRest = True
            else:
                nextIsRest = False
        else:
            nextIsRest = False

        nextStartTime = float(i) * (0.5 * song.ppq / 1000.0)
        nextPitch = melody[i%len(melody)]

        # add current note
        if i != 0:
            if not(currentIsRest):
                if nextIsRest:
                    song.addNote(0, currentPitch, currentStartTime, 0.99*duration, 0x40)
                else:
                    song.addNote(0, currentPitch, currentStartTime, 0.99*duration/2, 0x40)

        currentPitch = nextPitch
        currentStartTime = nextStartTime
        currentIsRest = nextIsRest


    # cymbal
    #for i in range(factor * len(notes) * 2):
    #    startTime = float(i) * (0.5 * song.ppq / 1000.0)
    #    song.addNote(1, 59, startTime, 0.99*duration/2, 0x40)

    
    return song
        





# todo: should give error if the item does not exist
def deleteSong(songName):

    p = db.getCurrentPopulation()
    print "deleting", p.title, songName
    result = p.amusic.engine.execute('DELETE FROM song WHERE population="%s" AND title="%s";' % (p.title, songName))
    #print result
    #print dir(result)


def currentPopulationSongNames():

    p = db.getCurrentPopulation()
    list = []
    result = p.amusic.engine.execute('SELECT title FROM song WHERE population="%s";'%(p.title)).fetchall()
    # each name is in a single element list, take away the single element list, so it's just a list of names
    for item in result:
        list.append(item[0])
    return list


def maxNumber():

    max = 0

    for name in currentPopulationSongNames():
        number = int(name[1:])
        if number > max:
            max = number

    return max


def nextNumber():
    global nextNumberValue
    nextNumberValue += 1
    return nextNumberValue


def copyAndMutateSong(originalSongName):

    newSongName = "s" + str(nextNumber() + 1)

    print "creating new song %s from %s" % (newSongName, originalSongName)

    # copy and mutate song
    song = db.getCurrentPopulation().Song(originalSongName)
    song.fromDB()
    song.title = newSongName
    song.mutate()
    song.toDB()


def printCurrentPopulation():

    print "------------------------------------------"
    print "population"
    print "------------------------------------------"
    count = 0
    for name in currentPopulationSongNames():
        print "%s." % count, name
        count += 1


def createNextGeneration(probabilities):

    print "create next generation:"
    print "probabilities", probabilities
    print "current population", currentPopulationSongNames()

    currentSize = len(currentPopulationSongNames())

    printCurrentPopulation()

    numberToAdd = sizeDuringReproduction - currentSize

    originalNamesList = currentPopulationSongNames()

    numberAdded = 0
    while numberAdded < numberToAdd:
        for name in originalNamesList:
            if probabilities == None or (random.random() < probabilities[name]):
                print name, "reproducing"
                copyAndMutateSong(name)
                numberAdded += 1
                if numberAdded >= numberToAdd: break
            else:
                print name, "skipped"

    printCurrentPopulation()


    print "------------------------------------------"
    numberToDelete = len(currentPopulationSongNames()) - sizeAfterReproduction
    numberDeleted = 0
    while numberDeleted < numberToDelete:
        for name in originalNamesList:
            if probabilities == None or (random.random() > probabilities[name]):
                print name, "deleting"
                deleteSong(name)
                numberDeleted += 1
                if numberDeleted >= numberToDelete: break
            else:
                print name, "skipped"


    printCurrentPopulation()




def printDecisions(decisions):

    for pair in decisions:
        print pair


def computeRatings_old(decisionSets):

    ratings = {}
    names = currentPopulationSongNames()
    for name in names:
        ratings[name] = 0

    #for decision in decisions:
    for decisionSet in decisionSets:
        for decision in decisionSet:
            songName = None
            if decision[2] == 'box1':
                songName = decision[0]
            elif decision[2] == 'box2':
                songName = decision[1]
            elif decision[2] == None:
                pass
            else:
                print "Error: invalid answer"
    
            if songName != None:
                ratings[songName] += 1

    return ratings


def computeRatings(decisionSets):

    ratings = {}
    names = currentPopulationSongNames()
    for name in names:
        ratings[name] = 0

    #for decision in decisions:
    for decisionSet in decisionSets:
        for decision in decisionSet:
            songName = None
            if decision[2] == 'box1':
                songName = decision[0]
            elif decision[2] == 'box2':
                # no point awarded if they pick this song, it's in the subset and only there for the sake of comparison
                pass
                #songName = decision[1]
            elif decision[2] == None:
                pass
            else:
                print "Error: invalid answer"
    
            if songName != None:
                ratings[songName] += 1

    return ratings


def computeProbabilities(decisions):

    ratings = computeRatings(decisions)
    probabilities = {}

    total = 0

    for key in ratings:
        total += ratings[key]

    for key in ratings:
        if total != 0:
            probabilities[key] = float(ratings[key]) / float(total)

    return probabilities






#createNextGeneration()
#sys.exit()



def initPopulationWithRandomSongs():

    db.initialize()

    db.setPopulation('p1')

    # make random songs
    createRandomSongs(sizeAfterReproduction)    
    #submitComparisons(db.getCurrentPopulation())


def initPopulationWithRepetitiveBassLines():

    db.initialize()

    db.setPopulation('p1')

    # make random songs
    createRandomSongs(sizeAfterReproduction)    
    #submitComparisons(db.getCurrentPopulation())




if doInitPopulationRandomly:
    initPopulationWithRandomSongs()	



#for i in range(numSongs):
#	songName = 's%d' % i
#	songs.append(songName)
#	ratings.append(0)

# initialize ratings
#names = currentPopulationSongNames()
#for name in names:
#    ratings[name] = 0



#def decisionsList():
#
#    currentSongs = currentPopulationSongNames()
#
#    # initialize decisions list
#    decisions = []
#    for i in range(len(currentSongs)):
#        for j in range(i+1, len(currentSongs)):
#            decisions.append([currentSongs[i], currentSongs[j], None])
#
#    return decisions



def restartPopulationEval(probabilities):

    db.setPopulation('p1')
    print "using population", 'p1'

    db.approveAllAssignments()
    time.sleep(3)
    if deleteEnabled: db.deleteHITs(True)
    print "deleted hits"
    print "list of hits (this should be empty):"
    db.listHITs(True)
    print
    createNextGeneration(probabilities)
    pairs = submitComparisons(db.getCurrentPopulation())
    print "pairs submitted"
    print pairs
    #initializeDecisionsList()
    time.sleep(3)

    return pairs



if doRestartPopulationEval:
    #global globalPairs
    globalPairs = restartPopulationEval(None)




def collectDecisions():

    while(True):

        while(True):
            try:
                print "trying get results"
                results = db.getResults()
                print "sleeping 4 seconds"
                time.sleep(4)
                break
            except:
                traceback.print_exc()
                print "trying get results again in 4 seconds"
                time.sleep(4)

        print "results from mechanical turk", results
        print "globalPairs", globalPairs


        # initialize decisions
        #decisions = []
        decisionSets = []
        for pair in globalPairs:
            decisionSet = []

            # create blank decision set
            for k in range(numAssignmentsPerHIT):

                decision = [pair[0], pair[1], None]

                if forceAllSelectionsArtificiallyForTesting:
                    decision[2] = 'box1'

                decisionSet.append(decision)


            decisionSets.append(decisionSet)

            #decision = [pair[0], pair[1], None]
            #decisions.append(decision)

        print "decisionSets", decisionSets

        print "number of results so far", len(results)

        # copy results from mechanical turk into decisions list
        for result in results:
            #for decision in decisions:
            for decisionSet in decisionSets:
                decisionExample = decisionSet[0]
                #print "check", result['Song1'], decisionExample[0]

                # if result Song1 and Song2 match, record the decision
                if result['Song1'] == decisionExample[0] + ".mp3" and result['Song2'] == decisionExample[1] + ".mp3":
                    print "MATCH"
                    # fill in the next open decision
                    for decision in decisionSet:
                        if decision[2] == None:
                            decision[2] = result['Answer']
                            break


        stillCollecting = False

        # determine if results still need to be collected
        print "decisions so far"
        #for item in decisions:
        #    print item
        #    if item[2] == None: stillCollecting = True
        for decisionSet in decisionSets:
            for decision in decisionSet:
                print decision
                if decision[2] == None:
                    stillCollecting = True
        print "end of decisions"

        computeRatingsResult = computeRatings(decisionSets)
        orderedResult = list(sorted(computeRatingsResult, key=computeRatingsResult.__getitem__, reverse=True))        
        print "ratings so far:"
        print computeRatingsResult
        print "ordered"
        print orderedResult

        #print "probabilities so far:"
        #print computeProbabilities(decisions)


        if stillCollecting:
            print "-------------------------------------------------------"
            print "still collecting results"
            print "-------------------------------------------------------"
            #print "ratings so far:", computeRatings(decisions)


        if not(stillCollecting):
            print "-------------------------------------------------------"
            print "finished collecting results or forcing restart"
            print "-------------------------------------------------------"

            print "sleeping"
            return






if doCollect:
    collectDecisions()


#add_population p1
#set_population p1
#add_repeat_song s1 8 0.3
#add_repeat_song s2 8 0.3
#add_repeat_song s3 8 0.3
#add_repeat_song s4 8 0.3
#synth_song s1 s1.mp3



if __name__ == '__main__':

    clearAllHITs = True

    if 1:
        createRepetitiveBassLines('temp', numBasslines=1)


    if 0:
        # create songs
        createRepetitiveBassLines('p1', numBasslines=9)

    if 0:
        print "deleting hits"
        if clearAllHITs: db.deleteHITs(True)


    if 0:
        # create hits
        print "deleting hits"
        if clearAllHITs: db.deleteHITs(True)
        print "numAssignmentsPerHIT", numAssignmentsPerHIT
        globalPairs = submitComparisons(db.getCurrentPopulation())
        print globalPairs
        filename = "globalPairs.pickle"
        file = open(filename, 'wb')
        pickle.dump(globalPairs, file)
        file.close()
        print "wrote", filename

    if 0:
        # collect results
        file = open("globalPairs.pickle", 'rb')
        globalPairs = pickle.load(file)
        print "len(globalPairs)", len(globalPairs)
        file.close()
        collectDecisions()


