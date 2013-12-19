
from amusic import *

db = initializePart1()

db.initialize()

db.setPopulation('p1')

# make 4 random songs

for i in range(0, 4):

	song = db.getCurrentPopulation().Song('s%d' % i)
	song.regularRepeat(8, 0.3)
	song.toDB()
	del song

	song = db.getCurrentPopulation().Song('s%d' % i)
	song.fromDB()
	song.synth('s%d.mp3' % i)

db.getCurrentPopulation().prepareBatch()


#add_population p1
#set_population p1
#add_repeat_song s1 8 0.3
#add_repeat_song s2 8 0.3
#add_repeat_song s3 8 0.3
#add_repeat_song s4 8 0.3
#synth_song s1 s1.mp3


