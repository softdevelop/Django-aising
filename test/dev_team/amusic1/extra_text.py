def printPairs(pairs):
	for pair in pairs:
		print pair,
		if pair[2] == 'box1':
			print pair[0]
		elif pair[2] == 'box2':
			print pair[1]
		elif pair[2] == None:
			print None
		else:
			print "Error"

