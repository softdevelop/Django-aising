import amusic1


# accesses database to print song intervals
def printSongIntervals(song):

    lastStartTime = 0

    try:
        songID,song.ppq = song.population.amusic.engine.execute('SELECT id,ppq FROM song WHERE title="%s" AND population="%s";'%(song.title, song.population.title)).fetchone()
    except TypeError:
        print "songs"
        list = song.population.amusic.engine.execute('SELECT * FROM song;')
        for item in list:
            print item
        raise Exception("SongNotFound")

    for tid,type,p,value,s,d,v in song.population.amusic.engine.execute('SELECT track,type,pitch,value,startTime,duration,velocity FROM event WHERE songID="%d";' % songID).fetchall():
        if type=='note':
            #print "(track,type,pitch,value,startTime,duration,velocity)", (tid,type,p,s,d,v)
            print s - lastStartTime
            lastStartTime = s




def testSongUtil():
        
    import amusic1
    db = amusic1.initialize()
    import songutil

    db.newPopulation('temp')
    db.setPopulation('temp')

    song = db.getCurrentPopulation().Song('EspanjaPrelude')
    song.fromFile("EspanjaPrelude.mid")

    printSongIntervals(song)




def copySongsInPopulation(inputPopulation, outputPopulation):

    
    db = amusic1.getDatabaseObject()
    
    
    #db.engine.execute('use amusic;')
    
    result = db.engine.execute('select * from song where population="%s"' % inputPopulation)
    db.engine.execute('use amusic')
    result = db.engine.execute('select * from song where population="%s"' % inputPopulation)
    result = db.engine.execute('select * from song where population="%s"' % inputPopulation)
    
    #result = db.engine.execute('show tables')
    
    db.setPopulation(inputPopulation)
    
    
    for item in result:
        #print item
        print item['title']
        name = item['title']
        # copy the song to permanent place in database
        song = db.getCurrentPopulation().Song(name)
        song.fromDB()
    
        db.newPopulation('permanent')
        population = db.getPopulation('permanent')
    
        song.population = population
        song.toDB()
        song.synth()



def createAndStoreBassline():

    db = amusic1.getDatabaseObject()
    import songeval
    #song = songeval.createRepetitiveBassLine((40, 41, 42, 43))
    #song.population = db.getPopulation('p1')
    #song.toDB()
    #song = songeval.createRepetitiveBassLine((40, 41, 42, 44), 'p1')
    #song.population = db.getPopulation('p1')
    #song.toDB()
    inputPopulation = 'p1'
    songeval.createRepetitiveBassLines(inputPopulation, numBasslines=1)
    result = db.engine.execute('select * from song where population="%s"' % inputPopulation)
    for row in result:
        print row

    copySongsInPopulation('p1', 'permanent')

    print "permanent"
    result = db.engine.execute('select * from song where population="%s"' % 'permanent')
    for row in result:
        print row




if __name__ == '__main__':


    #testSongUtil()
    #createAndStoreBassline()

