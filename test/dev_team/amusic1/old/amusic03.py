import sqlalchemy
import os
import random
import getpass
import sys
import subprocess
import csv
import boto
import ConfigParser
import re
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
        self.mtc = MTurkConnection(self.ACCESS_ID,self.SECRET_KEY,host='mechanicalturk.sandbox.amazonaws.com')
        try:
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
        except:pass
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
    def listHITs(self):
        print " ".join(('%s','%s','%s','%s','%s')) % ("HIT ID".ljust(30), "Status".ljust(22), "Amount", "Song1", "Song2")
        for i in self.mtc.search_hits(response_groups=['Request','Minimal','HITDetail','HITQuestion']):
            l = re.findall('<input type="hidden" value="([^"]+?)" name="song[12]" />',i.Question)
            print ' '.join((i.HITId, i.HITStatus,i.HITReviewStatus,i.Amount,l[0].split('/')[-1],l[1].split('/')[-1]))
    def deleteHITs(self):
        for i in self.mtc.get_reviewable_hits():
            self.mtc.dispose_hit(i.HITId)
    def approveAssignment(self,aID):
        self.mtc.approve_assignment(aID)
    def rejectAssignment(self,aID):
        self.mtc.reject_assignment(aID)
    def approveAllAssignments(self):
        for i in self.mtc.get_reviewable_hits():
            for assignment in self.mtc.get_assignments(i.HITId):
                if assignment.AssignmentStatus=="Submitted": 
                    self.mtc.approve_assignment(assignment.AssignmentId)
    def getResults(self):
        print " ".join(('%s','%s','%s','%s','%s')) % ("Assignment ID".ljust(30), "Worker ID".ljust(14), "Song1", "Song2", "Answer")
        for i in self.mtc.get_reviewable_hits():
            for assignment in self.mtc.get_assignments(i.HITId):
                ans = {}
                for j in assignment.answers[0]:
                    if j.qid!='commit': ans[j.qid] = j.fields[0].split('/')[-1]
                print assignment.AssignmentId, assignment.WorkerId,ans['song1'], ans['song2'], ans['boxradio']
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
                self.amusic.mtc.create_hit(hit_layout=self.amusic.conf['mturkLayoutID'],layout_params=params,reward=self.amusic.conf['hitRewardPerAssignment'],title=self.amusic.conf['hitTitle'],description=self.amusic.conf['hitDescription'],keywords=self.amusic.conf['hitKeywords'])
                n+=1

class Song(object):
    class PopulationNotFound( Exception ): pass
    def __init__(self, population, title):
        self.population = population
        self.title = title
        self.events = []
        self.ppq = 96
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
            l[2] += random.randint(-6,6)
            if l[2]<0: l[2]=0
            if l[2]>84: l[2]=84
            self.events[ev] = tuple(l)
            print l[2]
    def addNote(self, trackID, pitch, startTime, duration, velocity):
        self.events.append((trackID,'note',pitch,startTime,duration,velocity))
    def addTempo(self, value, startTime):
        self.events.append((0, 'tempo', value, startTime, 0, 0))
    def fromFile(self, fileName):
        class MIDItoNotes(MidiOutStream):
            currentNotes = {}
            ppq = 96
            currentTrack = 0
            outList = []
            def header(self, format=0, nTracks=1, division=96):
                self.ppq = division
            def start_of_track(self, n_track=0):
                self.currentTrack = n_track
            def note_on(self, channel=0, note=0x40, velocity=0x40):
                self.currentNotes[(self.currentTrack,note)] = (float(self.abs_time())/1000,velocity)
            def note_off(self, channel=0, note=0x40, velocity=0x40):
                self.outList.append((self.currentTrack,'note',note,self.currentNotes[(self.currentTrack,note)][0],float(self.abs_time())/1000-self.currentNotes[(self.currentTrack,note)][0],self.currentNotes[(self.currentTrack,note)][1]))
                del self.currentNotes[(self.currentTrack,note)]
            def tempo(self,value):
                self.outList.append((0,'tempo',value,float(self.abs_time())/1000,0,0))
        event_handler = MIDItoNotes()
        midi_in = MidiInFile(event_handler, fileName)
        midi_in.read()
        self.events = sorted(event_handler.outList,key=itemgetter(3,0))
        self.ppq = event_handler.ppq
    def toFile(self, fileName):
        self.events = sorted(self.events,key=itemgetter(3,0))
        tracks = list(set([i[0] for i in self.events]))
        midi_out = MidiOutFile(fileName)
        midi_out.header(nTracks=len(tracks),division=self.ppq)
        for i in tracks:
            midi_out.start_of_track(i)
            midi_out.update_time(0,relative=False)
            nl=[]
            for t,p,s,d,v in [x[1:] for x in self.events if x[0] == i]:
                if t == 'note':
                    nl.append((0,p,s,v))
                    nl.append((1,p,s+d,0))
                elif t == 'tempo':
                    nl.append((2,p,s,0))
            for t,p,s,v in sorted(nl,key=itemgetter(2)):
                midi_out.update_time(int(s*1000),relative=False)
                if   t == 0: midi_out.note_on (note=p, velocity=v)
                elif t == 1: midi_out.note_off(note=p)
                elif t == 2: midi_out.tempo(p)
            midi_out.end_of_track()
        midi_out.eof()
    def fromDB(self):
        self.clear()
        try:songID,self.ppq = self.population.amusic.engine.execute('SELECT id,ppq FROM song WHERE title="%s" AND population="%s";'%(self.title,self.population.title)).fetchone()
        except TypeError:
            raise SongNotFound
        for tid,type,p,value,s,d,v in self.population.amusic.engine.execute('SELECT track,type,pitch,value,startTime,duration,velocity FROM event WHERE songID="%d";' % songID).fetchall():
            if type=='note': self.events.append((tid,type,p,s,d,v))
            elif type=='tempo': self.events.append((tid,type,value,s,d,v))
    def toDB(self):
        self.events = sorted(self.events,key=itemgetter(3,0))
        try:
            songID = self.population.amusic.engine.execute('SELECT id FROM song WHERE title="%s" AND population="%s";'%(self.title,self.population.title)).fetchone()[0]
            self.population.amusic.engine.execute('DELETE FROM event WHERE songID="%d";'%(songID))
        except:
            self.population.amusic.engine.execute('INSERT INTO song (title,population,ppq) VALUES("%s","%s",%d);'%(self.title,self.population.title,self.ppq))
            songID = self.population.amusic.engine.execute('SELECT LAST_INSERT_ID();').fetchone()[0]
        for tid,type,p,s,d,v in self.events:
            if   type=='note':  self.population.amusic.engine.execute('INSERT INTO event (songID,track,type,pitch,startTime,duration,velocity) VALUES(%d,%d,"%s",%d,%f,%f,%d);'%(songID,tid,type,p,s,d,v))
            elif type=='tempo': self.population.amusic.engine.execute('INSERT INTO event (songID,track,type,value,startTime) VALUES(%d,%d,"%s",%d,%f);'%(songID,tid,type,p,s))
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
    def synth(self,fileName,upload=False):
        self.toFile('temp.mid')
        try:os.mkdir('tracks')
        except:pass
        print "\tGenerating MP3..."
        try:
            p=subprocess.Popen('fluidsynth/fluidsynth.exe -nli -r 44100 -g 1 -o synth.cpu-cores=2 -F temp.raw fluidsynth\Scc1t2.sf2 temp.mid'.split(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err=p.communicate()
            if p.wait()!=0:
                print err
                return False
        except KeyboardInterrupt:
            print "Interrupted"
            os.remove('temp.raw')
            return False
        os.remove('temp.mid')
        try:
            p=subprocess.Popen(['lame/lame.exe','-S','temp.raw','tracks/%s'%fileName], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out,err=p.communicate()
            if p.wait()!=0:
                print err
                return False
        except KeyboardInterrupt:
            print "Interrupted"
            os.remove('tracks/%s'%fileName)
            return False
        os.remove('temp.raw')
        if upload:
            def cb(cur,total):
                progress = int((float(cur)/total*40))
                print '\r\t|'+'='*progress+'-'*(40-progress)+'| %d%%'%(progress*2.5),
            print "\tUploading file to S3...",
            if not self.population.amusic.s3bucket: self.population.amusic.inits3()
            k = Key(self.population.amusic.s3bucket)
            k.key = 'tracks/%s' % fileName
            if k.exists(): k.open_read()
            if k.etag and k.compute_md5(open('tracks/'+fileName,'rb'))[0] == k.etag[1:-1]:
                print "up to date"
            else:
                print
                k.set_contents_from_filename('tracks/'+fileName,cb=cb,num_cb=40,replace=True)
                print '\n'
                k.set_acl('public-read')

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
        approve_hit <assignment id> (obtainable from get_results)
        reject_hit <assignment id> (obtainable from get_results)
        delete_hits
        approve_all
        get_results
"""



def parseargs(args):
    try:
        print args,sys.argv
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
            db.listHITs()
        elif args[0]=='approve_hit':
            db.approveAssignment(args[1])
        elif args[0]=='reject_hit':
            db.rejectAssignment(args[1])
        elif args[0]=='delete_hits':
            db.deleteHITs()
        elif args[0]=='approve_all':
            db.approveAllAssignments()
        elif args[0]=='get_results':
            db.getResults()
        else: raise ArgumentNotRecognized
    except IndexError:
        raise ArgumentsTooFew


def initializePart1():

    config = ConfigParser.ConfigParser()
    config.optionxform = str
    if os.path.exists('amusic.cfg'):
        config.read('amusic.cfg')
        username = config.get('Credentials','MySQLUsername')
        password  = config.get('Credentials','MySQLPassword')
        accessid  = config.get('Credentials','AWSAccessID')
        secretkey = config.get('Credentials','AWSSecretKey')
        assert username
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
        db.origconf['bucket'] = bucketname
        db.origconf['mturkLayoutID'] = defmturklid
        db.origconf['hitTitle'] = defhittitle
        db.origconf['hitDescription'] = defhitdesc
        db.origconf['hitKeywords'] = defhitkeyw
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


def initializePart2():
    if len(sys.argv)==1:
        while(True):
            cmd = raw_input('>>> ').strip()
            if cmd == 'exit': sys.exit()
            try: parseargs(cmd.split())
            except ArgumentNotRecognized:
                print "Invalid Argument"
    else: parseargs(sys.argv[1:])


if __name__ == '__main__':

    db = initializePart1()
    initializePart2()

