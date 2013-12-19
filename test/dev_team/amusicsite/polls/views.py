#Copyright 2013 Richard Giuly
#All rights reserved


# Create your views here.

#from django.shortcuts import render_to_response, get_object_or_404
#from django.http import Http404
#from django.template import RequestContext
#from polls.models import Poll

import sys
import os
sys.path.append('../amusic1')
from learn import *

import amusic1

from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext
from polls.models import Choice, Poll

from django.shortcuts import render
from django import forms

from django.core.servers.basehttp import FileWrapper



#from learn import *


#def index(request):
#    return HttpResponse('<form name="input" action="html_form_action.asp" method="get"> Username: <input type="text" name="user"> <input type="submit" value="Submit"> </form> ')




class ContactForm(forms.Form):
    #subject = forms.CharField(max_length=100)
    #message = forms.CharField()
    #sender = forms.EmailField()
    #midiSources = {}

    if 0:
        for root, dirs, filenames in os.walk("midi_source"):
            for filename in filenames:
                if filename.endswith('.mid'):
                    print filename
                    exec(os.path.splitext(filename)[0] + " = forms.BooleanField(required=False)")
                    #exec("channel_" + os.path.splitext(filename)[0] + " = forms.IntegerField(required=False, initial=0)")
                    #song = amusic1.Song('temp', 'tempName')
                    #song.fromFile(os.path.join("midi_source", filename))
                    #print "max track:", song.maxTrack()
                    #print "separated:", song.getSeparatedEvents().keys()
                    #x = forms.EmailField()
                    #y = forms.BooleanField(required=False)

    Rythm = forms.BooleanField(required=False)
    Harmony = forms.BooleanField(required=False)
    Chords = forms.BooleanField(required=False)
    Use_3_Time = forms.BooleanField(required=False)
    Sanity = forms.BooleanField(required=False)
    Fast_Tempo = forms.BooleanField(required=False)
    General_MIDI_Instrument_Number = forms.IntegerField(required=False, initial=0)
    MIDI_File_Output = forms.BooleanField(required=False)
    Experimental_Feature_Voice_Synth = forms.CharField(required=False)
    Two_Part_Tune_Maker = forms.BooleanField(required=False)


class UploadFileForm(forms.Form):

    #Upload_MIDI_Influence_File  = forms.FileField()
    file  = forms.FileField()



def about(request):
    return HttpResponse("""
    <h2><a href="/">aisings.com</a></h2> Founders: <br>  <a href="http://www.linkedin.com/in/rickgiuly">Rick Giuly</a><br>  <a href="http://www.austinsmithmusic.com">Austin Smith</a><br>
    <br>
    <hr>
    <br>
    <iframe width="420" height="315" src="//www.youtube.com/embed/haWJ4NwVHfI" frameborder="0" allowfullscreen></iframe>
    <iframe width="420" height="315" src="//www.youtube.com/embed/YwJQ9Rke1Tc" frameborder="0" allowfullscreen></iframe>
    """)


def stream(request):
    return HttpResponse("""
    <br>
    <h1> aisings stream </h1>
    <embed src='http://www.shoutcast.com/media/popupPlayer_V19.swf?stationid=http://yp.shoutcast.com/sbin/tunein-station.pls?id=12287&play_status=1' quality='high' bgcolor='#ffffff' width='398' height='104' name='popupPlayer_V19' align='middle' allowScriptAccess='always' allowFullScreen='true' type='application/x-shockwave-flash' pluginspage='http://www.adobe.com/go/getflashplayer' ></embed>
    <br>
    <br>
    <br>
    <h3>How to stream random songs from aisings.com to iTunes</h3>
    In iTunes, Advanced pulldown, open this stream:
    23.23.198.120:8000
    <br>
    <h3>Shoutcast site</h3> <a href=http://www.shoutcast.com/Internet-Radio/aisings>http://www.shoutcast.com/Internet-Radio/aisings</a> 
    <hr>
    <br>
    """)



def handleUploadedFile(file):

    print "uploaded file:", file

    with open(os.path.join('midi_source', str(file)), 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)


def uploadFile(request):

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            print "upload file form is valid"
            handleUploadedFile(request.FILES['file'])
            return HttpResponseRedirect('/finishedUpload')
        else:
            print "upload file form is not valid"
            print form.errors
            print request.POST
            print "files", request.FILES

    else:
        form = UploadFileForm()
    #return render_to_response('upload.html', {'form': form})
    return render(request, 'upload.html', {'form': form})


def finishedUpload(request):

    return HttpResponse('Finished upload <br><a href="/">Back to home</a>')


# main view
def index(request):

    influences = []
    for root, dirs, filenames in os.walk("midi_source"):
        for filename in filenames:
            if filename.endswith('.mid'):
                print filename
                influences.append(os.path.splitext(filename)[0])

    if request.method == 'POST': # If the form has been submitted...
        form = ContactForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            # ...
            return HttpResponseRedirect('/thanks/') # Redirect after POST
    else:
        form = ContactForm() # An unbound form

    return render(request, 'main.html', {
        'form': form,
        'influences': influences
    })





def songs(request):

    db = amusic1.getDatabaseObject()

    songs = []
    results = db.engine.execute('select * from song where population="%s"' % 'permanent')
    for item in results:
        filename = item['population'] + "_" + item['title'] + ".mp3.wav"
        fullFilename = os.path.join("..", "amusicsite", "polls", "static", "tracks", filename)
        print fullFilename
        if os.path.isfile(fullFilename):
            print "adding file", fullFilename
            songs.append({'filename':filename, 'title':item['title']})

    if request.method == 'POST': # If the form has been submitted...
        form = ContactForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            # ...
            return HttpResponseRedirect('/thanks/') # Redirect after POST
    else:
        form = ContactForm() # An unbound form

    print songs

    return render(request, 'songs.html', {
        'form': form,
        'influences': songs
    })




def result(request):

    print "request", request.POST

    #return HttpResponse("request " + str(request.POST)) # doesn't work

    if 0:
        # skip doing the operation
        myfile = open("temp.mid")
        response = HttpResponse(FileWrapper(myfile), content_type='audio/midi')
        response['Content-Disposition'] = 'attachment; filename=myfile.mid'
        return response


    errorStatus = runCreateProbabilitySong(request.POST)

    if errorStatus == "success":

        if 'MIDI_File_Output' in request.POST:
            myfile = open("temp.mid")
            response = HttpResponse(FileWrapper(myfile), content_type='audio/midi')
            response.set_cookie("fileDownloadToken", value='true')
            response['Content-Disposition'] = 'attachment; filename=myfile.mid'
        else:
            #myfile = open(os.path.join("tracks", "outputsong.mp3"))
            #response = HttpResponse(FileWrapper(myfile), content_type='audio/mpeg')
            #response['Content-Disposition'] = 'attachment; filename=myfile.mp3'
            myfile = open("temp.wav")
            response = HttpResponse(FileWrapper(myfile), content_type='audio/wav')
            response.set_cookie("fileDownloadToken", value='true')
            response['Content-Disposition'] = 'attachment; filename=myfile.wav'

        #render_to_response('result.html', {'title': "hello"})
    
        return response
    
        #return HttpResponse("result")

    else:

        return HttpResponse("Need to pick at least one influence." + str(request.POST))




def detail(request, poll_id):
    p = get_object_or_404(Poll, pk=poll_id)
    return render_to_response('polls/detail.html', {'poll': p},
                               context_instance=RequestContext(request))



def results(request, poll_id):
    p = get_object_or_404(Poll, pk=poll_id)
    return render_to_response('polls/results.html', {'poll': p})




def vote(request, poll_id):
    p = get_object_or_404(Poll, pk=poll_id)
    try:
        selected_choice = p.choice_set.get(pk=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the poll voting form.
        return render_to_response('polls/detail.html', {
            'poll': p,
            'error_message': "You didn't select a choice.",
        }, context_instance=RequestContext(request))
    else:
        selected_choice.votes += 1
        selected_choice.save()
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('polls.views.results', args=(p.id,)))


#def css(request):
#    templatesPath = os.path.join(os.getcwd(), "..", "templates")
#    fullPath = templatesPath + request.META['PATH_INFO']
#    with open(fullPath, 'r') as contentFile:
#        content = contentFile.read()
#    return HttpResponse(content)

