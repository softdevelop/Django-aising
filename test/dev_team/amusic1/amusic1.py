#Copyright 2013 Richard Giuly
#All rights reserved

import sqlalchemy
import os
import shutil
import random
import string
import getpass
import sys
import subprocess
import csv
import boto
import ConfigParser
import re
import shelve
import traceback
from datetime import timedelta
from boto.s3.key import Key
from boto.mturk.layoutparam import LayoutParameters,LayoutParameter
from boto.mturk.connection import MTurkConnection
from operator import itemgetter
from midi.MidiOutStream import MidiOutStream
from midi.MidiInFile import MidiInFile
from midi.MidiOutFile import MidiOutFile


class ArgumentsTooFew( Exception ): pass
class ArgumentNotRecognized( Exception ): pass
class SongNotFound( Exception ): pass
class PopulationNotFound( Exception ): pass


fontFolder = os.path.join("/home", "softdevelopinc", "amusic_files", "sound_fonts")

class amusic(object):
    engine = None
    origconf = {'minPitch':12,'maxPitch':84,'minStartTime':0.0,'maxStartTime':200.0,
                'minNoteDuration':0.5,'maxNoteDuration':5.0,'minNoteCount':50,'maxNoteCount':400,
                'currentPopulation':'','bucket':None,'hitRewardPerAssignment':0.05,'mturkLayoutID':None,
                'hitTitle':None,'hitDescription':None,'hitKeywords':None}
    conf = origconf.copy()
    s3bucket = None
    mtc = None
    class PopulationNotSet( Exception ): pass
    class SongNotFound( Exception ): pass
    def __init__(self,username,password,ACCESS_ID,SECRET_KEY,initialize=False):
        self.ACCESS_ID = ACCESS_ID
        self.SECRET_KEY = SECRET_KEY
        self.engine = sqlalchemy.create_engine('mysql+mysqlconnector://%s:%s@localhost' % (username,password))
        self.engine.connect()
        #self.mtc = MTurkConnection(self.ACCESS_ID,self.SECRET_KEY,host='mechanicalturk.sandbox.amazonaws.com')
        self.mtc = MTurkConnection(self.ACCESS_ID,self.SECRET_KEY,host='mechanicalturk.amazonaws.com')
        try:
            print "using amusic"
            self.engine.execute('USE amusic;')
            c = self.engine.execute('SELECT * FROM conf;').fetchone()
            self.conf['minPitch'] = c[0]
            self.conf['maxPitch'] = c[1]
            self.conf['minStartTime'] = c[2]
            self.conf['maxStartTime'] = c[3]
            self.conf['minNoteDuration'] = c[4]
            self.conf['maxNoteDuration'] = c[5]
            self.conf['minNoteCount'] = c[6]
            self.conf['maxNoteCount'] = c[7]
            self.conf['currentPopulation'] = c[8]
            self.conf['bucket'] = c[9]
            self.conf['mturkLayoutID'] = c[10]
            self.conf['hitTitle'] = c[11]
            self.conf['hitDescription'] = c[12]
            self.conf['hitKeywords'] = c[13]
            self.conf['hitRewardPerAssignment'] = c[14]
        except:
            print "error in amusic __init__"
            traceback.print_exc()
    def inits3(self):
        c = boto.connect_s3(self.ACCESS_ID,self.SECRET_KEY)
        self.s3bucket = c.create_bucket(self.conf['bucket'])
        self.s3bucket.set_acl('public-read')
    def initialize(self):
        try: self.engine.execute('DROP DATABASE IF EXISTS amusic;')
        except: pass
        self.engine.execute('CREATE DATABASE amusic;')
        self.engine.execute('USE amusic;')
        self.engine.execute('CREATE TABLE conf (minPitch INT,\
                                           maxPitch INT,\
                                           minStartTime FLOAT,\
                                           maxStartTime FLOAT,\
                                           minNoteDuration FLOAT,\
                                           maxNoteDuration FLOAT,\
                                           minNoteCount INT,\
                                           maxNoteCount INT,\
                                           currentPopulation VARCHAR(100),\
                                           bucket VARCHAR(100),\
                                           mturkLayoutID VARCHAR(100),\
                                           hitTitle VARCHAR(100),\
                                           hitDescription VARCHAR(100),\
                                           hitKeywords VARCHAR(100),\
                                           hitRewardPerAssignment FLOAT,\
                                           CONSTRAINT fk_1 FOREIGN KEY (`currentPopulation`) REFERENCES population (title),\
                                           PRIMARY KEY(minPitch)\
                                           ) ENGINE = MYISAM;')
        self.engine.execute('INSERT INTO conf (minPitch,\
                                          maxPitch,\
                                          minStartTime,\
                                          maxStartTime,\
                                          minNoteDuration,\
                                          maxNoteDuration,\
                                          minNoteCount,\
                                          maxNoteCount,\
                                          currentPopulation,\
                                          bucket,\
                                          hitRewardPerAssignment,\
                                          mturkLayoutID,\
                                          hitTitle,\
                                          hitKeywords,\
                                          hitDescription)\
                                          VALUES(%d,%d,%f,%f,%f,%f,%d,%d,"%s","%s",%f,"%s","%s","%s","%s");'%
                                          (self.origconf['minPitch'],self.origconf['maxPitch'],self.origconf['minStartTime'],
                                           self.origconf['maxStartTime'],self.origconf['minNoteDuration'],
                                           self.origconf['maxNoteDuration'],self.origconf['minNoteCount'],
                                           self.origconf['maxNoteCount'],self.origconf['currentPopulation'],
                                           self.origconf['bucket'], self.origconf['hitRewardPerAssignment'],
                                           self.origconf['mturkLayoutID'],self.origconf['hitTitle'],
                                           self.origconf['hitKeywords'],self.origconf['hitDescription']))
        self.engine.execute('CREATE TABLE population (title VARCHAR(100) NOT NULL,\
                                                 PRIMARY KEY(title)\
                                                 ) ENGINE = MYISAM;')
        self.engine.execute('CREATE TABLE song (id INT NOT NULL AUTO_INCREMENT,\
                                           title VARCHAR(100),\
                                           population VARCHAR(100),\
                                           ppq INT,\
                                           fitness FLOAT,\
                                           CONSTRAINT fk_1 FOREIGN KEY (`population`) REFERENCES population (title),\
                                           PRIMARY KEY(id,title)\
                                           ) ENGINE = MYISAM;')
        self.engine.execute('CREATE TABLE event (songID INT,\
                                            track INT,\
                                            id INT NOT NULL AUTO_INCREMENT,\
                                            type VARCHAR(5),\
                                            pitch INT,\
                                            value INT,\
                                            startTime FLOAT,\
                                            duration FLOAT,\
                                            velocity INT,\
                                            CONSTRAINT fk_1 FOREIGN KEY (`songID`) REFERENCES song (id),\
                                            PRIMARY KEY(songID,track,id)\
                                            ) ENGINE = MYISAM;')

    def setPopulation(self,title):
        self.engine.execute('UPDATE conf SET currentPopulation="%s";' % title)
        self.conf['currentPopulation'] = title
    def newPopulation(self,title):
        return Population(self,title)
    def getCurrentPopulation(self):
        if self.conf['currentPopulation'] == '':
            raise self.PopulationNotSet
        return Population(self,self.conf['currentPopulation'])
    def getPopulation(self,title):
        return Population(self,title,create=False)

    def listHITs(self,idonly):

        hits = self.getAllReviewableHits()

        if idonly:
            #for i in self.mtc.search_hits():
            for i in hits:
                print i.HITId
            return
        else:
            print " ".join(('%s','%s','%s','%s','%s')) % ("HIT ID".ljust(30), "Status".ljust(22), "Amount", "Song1", "Song2")
            #for i in self.mtc.search_hits(response_groups=['Request','Minimal','HITDetail','HITQuestion']):
            for i in hits:
                l1 = re.findall('<input type="hidden" value="([^"]+?)" name="song[12]" />', i.Question)
                l2 = re.findall('<input type="hidden" name="song[12]" value="([^"]+?)" />', i.Question)
		if len(l1) > 0: l = l1
		if len(l2) > 0: l = l2
		#print i.Question
                #inputs = re.findall('<input type="hidden".*?>',i.Question)
		#print "inputs", inputs
                if len(l)==2: print ' '.join((i.HITId, i.HITStatus,i.HITReviewStatus,i.Amount,l[0].split('/')[-1],l[1].split('/')[-1]))
                else: 
                    print "Error"
    def deleteHITs(self,all):
        #print "deleting 100 hits max"
        if all:
            while True:
                print "reading page"
                pageOfHits = self.mtc.search_hits(page_size=100)
                if len(pageOfHits) == 0: break
                print "finished reading page"
                for i in pageOfHits:

                    # approve all assignments (required for delete)
                    for assignment in self.mtc.get_assignments(i.HITId):
                        print "status", assignment.AssignmentStatus
                        if assignment.AssignmentStatus=="Submitted": 
                            self.mtc.approve_assignment(assignment.AssignmentId)

                    self.mtc.expire_hit(i.HITId)
                    try:
                        self.mtc.dispose_hit(i.HITId)
                        print "disposed without error, hit:", i.HITId
                    except:
                        print "could not dispose, hit", i.HITId
        else:
            for i in self.mtc.get_reviewable_hits(page_size=100):
                self.mtc.dispose_hit(i.HITId)
    def approveAssignment(self,aID):
        self.mtc.approve_assignment(aID)
    def rejectAssignment(self,aID):
        self.mtc.reject_assignment(aID)


    def getAllReviewableHits(self):

        tempHits = []
        page = 1

        while True:
            pageOfHits = self.mtc.search_hits(response_groups=['Request','Minimal','HITDetail','HITQuestion'], page_size=100, page_number=page)
            if len(pageOfHits) == 0: break
            tempHits += pageOfHits
            print "reading page", page
            page += 1

        return tempHits


    def approveAllAssignments(self):

        for i in self.getAllReviewableHits():
            print "approving", i.HITId
        #for i in self.mtc.get_reviewable_hits():
            for assignment in self.mtc.get_assignments(i.HITId):
                print "status", assignment.AssignmentStatus
                if assignment.AssignmentStatus=="Submitted": 
                    self.mtc.approve_assignment(assignment.AssignmentId)

    def getResults_old(self):
        print " ".join(('%s','%s','%s','%s','%s')) % ("Assignment ID".ljust(30), "Worker ID".ljust(14), "Song1", "Song2", "Answer")
        for i in self.mtc.get_reviewable_hits():
            for assignment in self.mtc.get_assignments(i.HITId):
                ans = {}
                for j in assignment.answers[0]:
                    if j.qid!='commit': ans[j.qid] = j.fields[0].split('/')[-1]
                print assignment.AssignmentId, assignment.WorkerId,ans['song1'], ans['song2'], ans['boxradio']

    def getResults(self):

        print "starting get results"
        print " ".join(('%s','%s','%s','%s','%s')) % ("Assignment ID".ljust(30), "Worker ID".ljust(14), "Song1", "Song2", "Answer")
        results = []
        hits = []
        page = 1

        while True:
            pageOfHits = self.mtc.get_reviewable_hits(page_size=100, page_number=page)
            if len(pageOfHits) == 0: break
            hits += pageOfHits
            page += 1

        hitCount = 0
        for i in hits:
            assignmentsForThisHIT = self.mtc.get_assignments(i.HITId)
            print "HIT %d total number %d" % (hitCount, len(hits)), "  NumResults", assignmentsForThisHIT.NumResults

            for assignment in assignmentsForThisHIT:
                ans = {}
                for j in assignment.answers[0]:
                    if j.qid!='commit': ans[j.qid] = j.fields[0].split('/')[-1]
                print assignment.AssignmentId, assignment.WorkerId,ans['song1'], ans['song2'], ans['boxradio']
                resultDict = {'AssignmentId':[assignment.AssignmentId], 'WorderID':assignment.WorkerId, 'Song1':ans['song1'], 'Song2':ans['song2'], 'Answer':ans['boxradio']}
                results.append(resultDict)
            hitCount += 1
        #print results
        print "finished get results"
        return results


class Population(object):
    def __init__(self,amusic,title,create=True):
        self.amusic = amusic
        if self.amusic.engine.execute('SELECT title FROM population WHERE title="%s";' % title).fetchone() == None:
            if create: self.amusic.engine.execute('INSERT INTO population (title) VALUES("%s");'%title)
            else: raise PopulationNotFound
        self.title = title
    def Song(self,title):
        return Song(self,title)
    def prepareBatch(self):
	print "mturkLayoutID", self.amusic.conf['mturkLayoutID']
        if not self.amusic.conf['mturkLayoutID']:
            print "LayoutID not set"
            return
        l = [i[0] for i in self.amusic.engine.execute('SELECT title FROM song WHERE population="%s";'%(self.title)).fetchall()]
        for d,i in enumerate(l):
            print 'Song %d/%d (%s)'%(d+1,len(l),i)
            s = Song(self,i)
            s.fromDB()
            s.synth(i+'.mp3' if i.find('.')==-1 else i[:i.find('.')]+'.mp3',upload=True)
        print "Creating HITs..."
        print "host:", self.amusic.mtc.host
        s = "http://%s.s3.amazonaws.com/tracks/" % (self.amusic.conf['bucket'])
        n=1
        for d,i in enumerate(l):
            for j in l[d+1:]:
                f1 = i+'.mp3' if i.find('.')==-1 else i[:i.find('.')]+'.mp3'
                f2 = j+'.mp3' if j.find('.')==-1 else j[:j.find('.')]+'.mp3'
                print "\tHIT %d/%d (%s,%s)" % (n,len(l)*(len(l)-1)/2,f1,f2)
                params = LayoutParameters()
                params.add(LayoutParameter('file1',s+f1))
                params.add(LayoutParameter('file2',s+f2))
                #self.amusic.mtc.create_hit(hit_layout=self.amusic.conf['mturkLayoutID'],layout_params=params,reward=self.amusic.conf['hitRewardPerAssignment'],title=self.amusic.conf['hitTitle'],description=self.amusic.conf['hitDescription'],keywords=self.amusic.conf['hitKeywords'],duration=timedelta(minutes=4),lifetime=timedelta(minutes=40))
                self.amusic.mtc.create_hit(hit_layout=self.amusic.conf['mturkLayoutID'],layout_params=params,reward=0.03,title=self.amusic.conf['hitTitle'],description=self.amusic.conf['hitDescription'],keywords=self.amusic.conf['hitKeywords'],duration=timedelta(minutes=4),lifetime=timedelta(minutes=40))
                n+=1

class Song(object):

    class PopulationNotFound( Exception ): pass




    def __init__(self, population, title):
        self.population = population
        self.title = title
        self.events = []
        self.ppq = 96

        self.channelForTrack = [0, 0]
        self.patchForTrack = [0, 0]

        # track 0
        self.channelForTrack[0] = 0
        self.patchForTrack[0] = 87
        
        # track 1
        self.channelForTrack[1] = 9
        self.patchForTrack[1] = 0



    def copy(self, title):
        s = Song(self.population, title)
        s.events = list(self.events)
        return s

    def mutate(self):
        n = random.randint(1,3)
        for i in range(n):
            ev = random.randint(0,len(self.events)-1)
            while(self.events[ev][1] == 'tempo'): ev = random.randint(0,len(self.events)-1)
            l = list(self.events[ev])
            print str(ev+1)+":",l[2],"=>",

            selection = random.randint(0,2)

            if selection == 0:
                # change pitch
                l[2] += random.randint(-6, 6)
                if l[2]<0: l[2]=0
                if l[2]>84: l[2]=84
            elif selection == 1:
                # change velocity
                l[5] += random.randint(-20, 20)
                if l[5]<0: l[5]=0
                if l[5]>255: l[5]=255
            elif selection == 2:
                # change velocity to 255 or 0
                if random.randint(0, 1) == 1:
                    l[5] = 255
                else:
                    l[5] = 0


            self.events[ev] = tuple(l)
            print l[2]

    def addNote(self, trackID, pitch, startTime, duration, velocity):
        patch = 0 # this is pretty much ignored. doesn't make a whole lot of sense as a patch is assigned to a channel (as the code works right now)
        channel = 0 # this is pretty much ignored. doesn't make a whole lot of sense as a channel is assigned by track (as the code works right now)
        self.events.append((trackID, 'note', pitch, startTime, duration, velocity, channel, patch))
    def addTempo(self, value, startTime):
        channel = 0
        patch = 0
        self.events.append((0, 'tempo', value, startTime, 0, 0, channel, patch))

    def fromFile(self, filename):
        class MIDItoNotes(MidiOutStream):
            currentNotes = {}
            ppq = 96
            currentTrack = 0
            outList = []
            def header(self, format=0, nTracks=1, division=96):
                self.ppq = division
            def start_of_track(self, n_track=0):
                self.currentTrack = n_track
                print "start_of_track", n_track
            def note_on(self, channel=0, note=0x40, velocity=0x40):
                self.currentNotes[(self.currentTrack,note)] = (float(self.abs_time())/1000,velocity)
            def note_off(self, channel=0, note=0x40, velocity=0x40):
                patch = 1
                if (self.currentTrack, note) in self.currentNotes:
                    out = (self.currentTrack,
                          'note',
                          note,
                          self.currentNotes[(self.currentTrack, note)][0],
                          float(self.abs_time())/1000-self.currentNotes[(self.currentTrack, note)][0],
                          self.currentNotes[(self.currentTrack, note)][1],
                          channel,
                          patch)
                    #print "out:", out
                    self.outList.append(out)
                    del self.currentNotes[(self.currentTrack, note)]
            def tempo(self,value):
                channel = 0
                patch = 0
                self.outList.append((0,'tempo',value,float(self.abs_time())/1000,0,0,channel,patch))
            def patch_change(self, channel, patch):
                print "patch_change", "channel", channel, "patch", patch
                #self.currentChannel = channel
                #self.currentPatch = patch
            def sysex_event(self, parameter):
                print "sysex", parameter
            #def midi_ch_prefix(self, channel):
            #    print "midi channel:", channel

        event_handler = MIDItoNotes()
        midi_in = MidiInFile(event_handler, filename)

        print "starting read", filename
        try:
            midi_in.read()
        except:
            #todo: this is a hack, it just renames files it can't read
            print "renaming file so it won't be accessed again"
            os.rename(filename, filename + "_unreadable")
        print "finished read", filename

        # probably should not sort like this, who knows, seems like some things could get out of order
        self.events = sorted(event_handler.outList,key=itemgetter(3,0))
        self.ppq = event_handler.ppq



    #def toFile(self, filename, patch=0):
    def toFile(self, filename):

        print "to file", filename

        self.events = sorted(self.events, key=itemgetter(3, 0))

        # count number of unique tracks
        tracks = list(set([i[0] for i in self.events]))

        midi_out = MidiOutFile(filename)

        midi_out.header(nTracks=len(tracks), division=self.ppq)


        for i in tracks:
            midi_out.start_of_track(i)
            midi_out.patch_change(self.channelForTrack[i], self.patchForTrack[i])
            midi_out.update_time(0,relative=False)
            nl=[]
            # for this track, build a note list
            for t,p,s,d,v,channel,patch in [x[1:] for x in self.events if x[0] == i]:
                if t == 'note':
                    print "on", (0,p,s,v,channel,patch)
                    print "off", (1,p,s+d,0,channel,patch)
                    nl.append((0,p,s,v,channel,patch))
                    nl.append((1,p,s+d,0,channel,patch))
                elif t == 'tempo':
                    nl.append((2,p,s,0,channel,patch))
            # for this track, sort the note list by start time and send it to midi file writer
            # t is for type
            for t,p,s,v,channel,patch in sorted(nl,key=itemgetter(2)):
                midi_out.update_time(int(s*1000), relative=False)
                if   t == 0:
                    midi_out.note_on(channel=self.channelForTrack[i], note=p, velocity=v)
                    #print "note on event"
                elif t == 1: midi_out.note_off(channel=self.channelForTrack[i], note=p)
                elif t == 2:
                    print "tempo event"
                    midi_out.tempo(p)
            midi_out.end_of_track()
        midi_out.eof()


    def fromDB(self):

        self.clear()
        try:songID,self.ppq = self.population.amusic.engine.execute('SELECT id,ppq FROM song WHERE title="%s" AND population="%s";'%(self.title,self.population.title)).fetchone()
        except TypeError:
            # print out songs
            print "songs"
            list = self.population.amusic.engine.execute('SELECT * FROM song;')
            for item in list:
                print item
            raise Exception("SongNotFound")
        for tid,type,p,value,s,d,v in self.population.amusic.engine.execute('SELECT track,type,pitch,value,startTime,duration,velocity FROM event WHERE songID="%d";' % songID).fetchall():
            channel = 0
            patch = 0
            if type=='note': self.events.append((tid,type,p,s,d,v,channel,patch))
            elif type=='tempo': self.events.append((tid,type,value,s,d,v,channel,patch))

        filename = "shelve_database"
        dict = shelve.open(filename)
        try:
            self.channelForTrack = dict[str(self.title)]['channelForTrack']
            self.patchForTrack = dict[str(self.title)]['patchForTrack']
        except:
            self.channelForTrack = (0, 0)
            self.patchForTrack = (0, 0)
            traceback.print_exc()
        dict.close()



    def toDB(self):

        self.events = sorted(self.events,key=itemgetter(3,0))
        try:
            songID = self.population.amusic.engine.execute('SELECT id FROM song WHERE title="%s" AND population="%s";'%(self.title,self.population.title)).fetchone()[0]
            self.population.amusic.engine.execute('DELETE FROM event WHERE songID="%d";'%(songID))
        except:
            self.population.amusic.engine.execute('INSERT INTO song (title,population,ppq) VALUES("%s","%s",%d);'%(self.title,self.population.title,self.ppq))
            songID = self.population.amusic.engine.execute('SELECT LAST_INSERT_ID();').fetchone()[0]
        for tid,type,p,s,d,v,channel,patch in self.events:
            if   type=='note':  self.population.amusic.engine.execute('INSERT INTO event (songID,track,type,pitch,startTime,duration,velocity) VALUES(%d,%d,"%s",%d,%f,%f,%d);'%(songID,tid,type,p,s,d,v))
            elif type=='tempo': self.population.amusic.engine.execute('INSERT INTO event (songID,track,type,value,startTime) VALUES(%d,%d,"%s",%d,%f);'%(songID,tid,type,p,s))


        #hack: putting this information in the shelve database rather than mysql
        # it may be better to just put everything in shelve
        filename = "shelve_database"
        dict = shelve.open(filename)
        dict[str(self.title)] = {'channelForTrack': self.channelForTrack, 'patchForTrack': self.patchForTrack}
        dict.close()


    def random(self):
        self.clear()
        self.addTempo(60000000/120,0)
        t=60000.0/120.0/self.ppq
        for i in range(random.randint(self.population.amusic.conf['minNoteCount'],self.population.amusic.conf['maxNoteCount'])):
            tmp = (0,random.randint(self.population.amusic.conf['minPitch'],self.population.amusic.conf['maxPitch']),
                           random.uniform(self.population.amusic.conf['minStartTime'],self.population.amusic.conf['maxStartTime'])/t,
                           random.uniform(self.population.amusic.conf['minNoteDuration'],self.population.amusic.conf['maxNoteDuration'])/t,0x40)
            self.addNote(*tmp)
        for i in self.events: print i
    def regular(self, num, interval):
        self.clear()
        self.addTempo(60000000/120,0)
        t=60000.0/120.0/self.ppq
        for i in range(num):
            self.addNote(0,random.randint(self.population.amusic.conf['minPitch'],self.population.amusic.conf['maxPitch']),(i*interval*2+interval)/t,interval/t,0x40)
    def regularRepeat(self, num, interval):
        self.clear()
        self.addTempo(60000000/120,0)
        t=60000.0/120.0/self.ppq
        noteList = []
        for i in range(num):
            noteList.append(random.randint(self.population.amusic.conf['minPitch'],self.population.amusic.conf['maxPitch']))
        count = 0
        for repeat in range(4):
            for i in range(num):
                count += 1
                self.addNote(0,noteList[i],(count*interval*2+interval)/t,interval/t*4,0x40)
    def clear(self):
        self.notes = []
        self.tracks = []

    def _print(self):
        print '+-------+-------+-------+--------+-----------+----------+----------+'
        print '| track | type  | pitch | value  | startTime | duration | velocity |'
        print '+-------+-------+-------+--------+-----------+----------+----------+'
        for i in self.events:
            if i[1] == 'note':
                print ('| %s '*7+'|') % (str(i[0]).ljust(5), str(i[1]).ljust(5),
                                       str(i[2]).ljust(5), str('').ljust(6),
                                       str(i[3]).ljust(9), str(i[4]).ljust(8),
                                       str(i[5]).ljust(8))
            elif i[1] == 'tempo':
                print ('| %s '*7+'|') % (str(i[0]).ljust(5), str(i[1]).ljust(5),
                                          str(i[2]).ljust(5), str(i[3]).ljust(6),
                                          str('').ljust(9), str(i[4]).ljust(8),
                                          str(i[5]).ljust(8))
        print '+-------+-------+-------+--------+-----------+----------+----------+'


    def filename(self):
        #todo: should not be title.title like that
        filename = "%s_%s.%s" % (self.population.title, self.title, "mp3")
        print "filename", filename
        return filename

    #def synth(self, filename, upload=False, patch=0, generateMP3=False):
    def synth(self, filename=None, upload=False, generateMP3=False, tempFilename="temp"):

        if filename == None:
            filename = self.filename() 

        self.toFile(tempFilename + '.mid')
        print "\tGenerating..."

        #if os.name == 'nt':
        #    fileFolder = os.path.join("..", "..", "..", "..", "amusic_files", "sound_fonts")
        #else:
        #    fileFolder = os.path.join("..", "..", "..", "..", "amusic_files", "sound_fonts")

        staticFolder = os.path.join("..", "amusicsite", "polls", "static")

        fullFilename = os.path.join(staticFolder, 'tracks', filename)


        try:os.mkdir(os.path.join(staticFolder, 'tracks'))
        except:pass
     

        if not(os.path.isdir(fontFolder)):
            raise Exception("font folder does not exist " + fontFolder)

        fontFilename = "WeedsGM3.sf2"
        #fontFilename = random.choice(os.listdir(fontFolder))
        #fontFilename = "1115-Filter_Bass_1.SF2"
        #if " " in fontFilename:
        #    newFilename = string.replace(fontFilename, " ", "_")
        #    os.rename(os.path.join(fontFolder, fontFilename), os.path.join(fontFolder, newFilename))
        #    fontFilename = newFilename

        #soundFontFile = os.path.join("fluidsynth", "Scc1t2.sf2")
        soundFontFile = os.path.join(fontFolder, fontFilename)
        #soundFontFile = r"I:\downloads\Saber_5ths_and_3rds\Saber_5ths_and_3rds.sf2"
        #I:\downloads\BassFing

        if not(os.path.isfile(soundFontFile)):
            raise Exception("file does not exist " + soundFontFile)

        try:
            if os.name == 'nt':
                print os.getcwd()
                print "using fluidsynth command for Windows"
                #p=subprocess.Popen('fluidsynth/fluidsynth.exe -nli -r 44100 -g 1 -o synth.cpu-cores=2 -F temp.raw fluidsynth\Scc1t2.sf2 temp.mid'.split(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                commandLine = (os.path.join("fluidsynth", "fluidsynth.exe") + ' -nli -r 44100 -g 1 -o synth.cpu-cores=2 -F ' + tempFilename + '.wav ' + soundFontFile + ' ' + tempFilename + '.mid')
                print commandLine
                #p=subprocess.Popen(commandLine.split(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            else:
                print "using fluidsynth command for Linux"
                #p=subprocess.Popen('fluidsynth -nli -r 44100 -g 1 -o synth.cpu-cores=2 -F temp.raw fluidsynth/Scc1t2.sf2 temp.mid'.split(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                commandLine = ('fluidsynth -nli -r 44100 -g 1 -o synth.cpu-cores=2 -F ' + tempFilename + '.wav ' + soundFontFile + ' ' + tempFilename + '.mid')
                print commandLine
                #p=subprocess.Popen(commandLine.split(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            print "running fluidsynth"
            os.system(commandLine)
            #out,err=p.communicate()
            #if p.wait()!=0:
            #    print err
            #    return False
            print "finished fluidsynth"
        except KeyboardInterrupt:
            print "Interrupted"
            #os.remove('temp.raw')
            return False
        #os.remove('temp.mid')
        try:
            #print os.getcwd()
            if generateMP3:
               
                # mp3 file
                print "generating:"
                print os.path.join(os.getcwd(), fullFilename)
                if os.name == 'nt':
                    print "using lame (mp3 codec) command for Windows"
                    #p=subprocess.Popen(['lame/lame.exe','-S','temp.raw','tracks/%s'%filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    p=subprocess.Popen(['lame/lame.exe','-S',tempFilename + '.wav',fullFilename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                else:
                    print "using lame (mp3 codec) command for Linux"
                    #p=subprocess.Popen(['lame','-S','temp.raw','tracks/%s'%filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    p=subprocess.Popen(['lame','-S',tempFilename + '.wav',fullFilename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out,err=p.communicate()
                if p.wait()!=0:
                    print err
                    return False
            else:
                # wave file
                print os.path.join(os.getcwd(), fullFilename + ".wav")
                shutil.copyfile(tempFilename + ".wav", fullFilename + ".wav")
        except KeyboardInterrupt:
            print "Interrupted"
            os.remove(fullFilename)
            return False
        #os.remove('temp.raw')
        if upload:
            def cb(cur,total):
                progress = int((float(cur)/total*40))
                print '\r\t|'+'='*progress+'-'*(40-progress)+'| %d%%'%(progress*2.5),
            print "\tUploading file %s to S3..." % filename,
            if not self.population.amusic.s3bucket: self.population.amusic.inits3()
            k = Key(self.population.amusic.s3bucket)
            k.key = 'tracks/%s' % filename
            if k.exists(): k.open_read()
            if k.etag and k.compute_md5(open('tracks/'+filename,'rb'))[0] == k.etag[1:-1]:
                print "up to date"
            else:
                print
                k.set_contents_from_filename('tracks/'+filename,cb=cb,num_cb=40,replace=True)
                print '\n'
                k.set_acl('public-read')


    def maxTrack(self):

        trackIndex = 0
        max = 0
        for event in self.events:
            if event[trackIndex] > max:
                max = event[trackIndex]
        return max


    def getSeparatedEvents(self):

        trackIndex = 0
        channelIndex = 6
        patchIndex = 7
        separatedEvents = {}
        for event in self.events:
            key = (event[trackIndex], event[channelIndex], event[patchIndex])
            if key in separatedEvents:
                separatedEvents[key].append(event)
            else:
                separatedEvents[key] = [event]
        return separatedEvents


helpstring=""" Available commands:
        init (Initializes DB)
        add_population <title>
        set_population <title>
        add_random_song <title>
        import_song <filename>
        export_song <title> <filename>
        print_song <title>
        synth_song <title> <filename>
        submit_hits
        list_hits
        list_all_hits (only lists ID)
        delete_hits (only reviewable hits)
        delete_all_hits (all hits)
        approve_hit <assignment id> (obtainable from get_results)
        reject_hit <assignment id> (obtainable from get_results)
        approve_all
        get_results
"""



def parseargs(args):
    try:
        if args[0]=='help':
            print helpstring
            sys.exit()
        elif args[0]=='init': db.initialize()
        elif args[0]=='add_population':
            db.newPopulation(args[1])
        elif args[0]=='set_population':
            db.setPopulation(args[1])
        elif args[0]=='add_random_song':
            song = db.getCurrentPopulation().Song(args[1])
            song.random()
            song.toDB()
            del song
        elif args[0]=='add_regular_song':
            song = db.getCurrentPopulation().Song(args[1])
            song.regular(int(args[2]),float(args[3]))
            song.toDB()
            del song
        elif args[0]=='add_repeat_song':
            song = db.getCurrentPopulation().Song(args[1])
            song.regularRepeat(int(args[2]),float(args[3]))
            song.toDB()
            del song
        elif args[0]=='copy_song':
            song = db.getCurrentPopulation().Song(args[1])
            song.fromDB()
            song.title = args[2]
            song.toDB()
            del song
        elif args[0]=='mutate_song':
            song = db.getCurrentPopulation().Song(args[1])
            song.fromDB()
            song.mutate()
            song.toDB()
            del song
        elif args[0]=='import_song':
            song = db.getCurrentPopulation().Song(args[1])
            song.fromFile(args[1])
            song.toDB()
        elif args[0]=='export_song':
            song = db.getCurrentPopulation().Song(args[1])
            song.fromDB()
            song.toFile(args[2])
        elif args[0]=='print_song':
            song = db.getCurrentPopulation().Song(args[1])
            song.fromDB()
            song._print()
        elif args[0]=='synth_song':
            song = db.getCurrentPopulation().Song(args[1])
            song.fromDB()
            song.synth(args[2])
        elif args[0]=='submit_hits':
            db.getCurrentPopulation().prepareBatch()
        elif args[0]=='list_hits':
            db.listHITs(False)
        elif args[0]=='list_all_hits':
            db.listHITs(True)
        elif args[0]=='approve_hit':
            db.approveAssignment(args[1])
        elif args[0]=='reject_hit':
            db.rejectAssignment(args[1])
        elif args[0]=='delete_hits':
            db.deleteHITs(False)
        elif args[0]=='delete_all_hits':
            db.deleteHITs(True)
        elif args[0]=='approve_all':
            db.approveAllAssignments()
        elif args[0]=='get_results':
            db.getResults()
        else: raise ArgumentNotRecognized
    except IndexError:
        raise ArgumentsTooFew


# old initialize part 1
def getDatabaseObject():

    config = ConfigParser.ConfigParser()
    config.optionxform = str
    if os.path.exists('amusic.cfg'):
        print "reading", "amusic.cfg"
        config.read('amusic.cfg')
        username = config.get('Credentials','MySQLUsername')
        password  = config.get('Credentials','MySQLPassword')
        accessid  = config.get('Credentials','AWSAccessID')
        secretkey = config.get('Credentials','AWSSecretKey')
        assert username, "no user name in config file, current directory is %s" % os.getcwd()
        assert accessid
        assert secretkey
        db = amusic(username,password,accessid,secretkey)
        bucketname = config.get('Defaults','S3Bucket')
        defmturklid = config.get('Defaults','MTurkLayoutID')
        defhittitle = config.get('Defaults','HITTitle')
        defhitdesc = config.get('Defaults','HITDescription')
        defhitkeyw = config.get('Defaults','HITKeywords')
        assert bucketname
        assert defmturklid
        assert defhittitle
        assert defhitdesc
        assert defhitkeyw
        #db.origconf['mturkLayoutID'] = defmturklid
        db.conf['bucket'] = bucketname
        db.conf['mturkLayoutID'] = defmturklid
        db.conf['hitTitle'] = defhittitle
        db.conf['hitDescription'] = defhitdesc
        db.conf['hitKeywords'] = defhitkeyw
        return db
    else:
        config.add_section('Credentials')
        config.add_section('Defaults')
        config.set('Credentials','MySQLUsername','')
        config.set('Credentials','MySQLPassword','')
        config.set('Credentials','AWSAccessID','')
        config.set('Credentials','AWSSecretKey','')
        config.set('Defaults','S3Bucket','')
        config.set('Defaults','MTurkLayoutID','')
        config.set('Defaults','HITTitle','')
        config.set('Defaults','HITDescription','')
        config.set('Defaults','HITKeywords','')
        config.write(open('amusic.cfg','wb'))
        print "Empty config file created. Please fill and rerun."
        exit()
    #if os.path.exists('passwd'):
        #username,password,accessid,secretkey = open('passwd').read().split()
    #else:
        #username = raw_input("Enter MySQL Username:")
        #password = getpass.getpass("Enter MySQL Password:")
        #accessid = raw_input("Enter AWS Access ID:")
        #secretkey = getpass.getpass("Enter AWS Secret Key:")


# old initialize part 2
def startCommandExecution():
    if len(sys.argv)==1:
        while True:
            cmd = raw_input('>>> ').strip()
            if cmd == 'exit': sys.exit()
            try: parseargs(cmd.split())
            except ArgumentNotRecognized:
                print "Invalid Argument"
    else: parseargs(sys.argv[1:])



if __name__ == '__main__':

    db = getDatabaseObject()
    startCommandExecution()

