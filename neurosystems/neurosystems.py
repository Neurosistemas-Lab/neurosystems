def hope(my_name):
    """
    Print a line for testing package import
    Args:
        my_name (str): person's name
    Returns:
        None
    """

    print(f"I'll contain all Neurosystema's Lab functions some day, {my_name}.")
    
# EDF Reader
#
# Does not actually read EDFs directly, but the ASC files that are produced
# by edf2asc (SR Research). Information on saccades, fixations and blinks is
# read from the EDF, therefore based on SR Research algorithms. For optimal
# event detection, it might be better to use a different algorithm, e.g.
# Nystrom, M., & Holmqvist, K. (2010). An adaptive algorithm for fixation,
# saccade, and glissade detection in eyetracking data. Behavior Research
# Methods, 42, 188-204. doi:10.3758/BRM.42.1.188
#
# (C) Edwin Dalmaijer, 2013-2014
# edwin.dalmaijer@gmail.com
#
# Modified from version 2 (24-Apr-2014)

__author__ = "Edwin Dalmaijer"


import copy
import os.path

import numpy


def replace_missing(value, missing=0.0):
	
	"""Returns missing code if passed value is missing, or the passed value
	if it is not missing; a missing value in the EDF contains only a
	period, no numbers; NOTE: this function is for gaze position values
	only, NOT for pupil size, as missing pupil size data is coded '0.0'
	
	arguments
	value		-	either an X or a Y gaze position value (NOT pupil
					size! This is coded '0.0')
	
	keyword arguments
	missing		-	the missing code to replace missing data with
					(default = 0.0)
	
	returns
	value		-	either a missing code, or a float value of the
					gaze position
	"""
	
	if value.replace(' ','') == '.':
		return missing
	else:
		return float(value)

def read_edf(filename, start, stop=None, missing=0.0, debug=False):
	
	"""Returns a list with dicts for every trial. A trial dict contains the
	following keys:
		x		-	numpy array of x positions
		y		-	numpy array of y positions
		size		-	numpy array of pupil size
		time		-	numpy array of timestamps, t=0 at trialstart
		trackertime	-	numpy array of timestamps, according to EDF
		events	-	dict with the following keys:
						Sfix	-	list of lists, each containing [starttime]
						Ssac	-	list of lists, each containing [starttime]
						Sblk	-	list of lists, each containing [starttime]
						Efix	-	list of lists, each containing [starttime, endtime, duration, endx, endy]
						Esac	-	list of lists, each containing [starttime, endtime, duration, startx, starty, endx, endy]
						Eblk	-	list of lists, each containing [starttime, endtime, duration]
						msg	-	list of lists, each containing [time, message]
						NOTE: timing is in EDF time!
	
	arguments
	filename		-	path to the file that has to be read
	start		-	trial start string
	
	keyword arguments
	stop			-	trial ending string (default = None)
	missing		-	value to be used for missing data (default = 0.0)
	debug		-	Boolean indicating if DEBUG mode should be on or off;
				if DEBUG mode is on, information on what the script
				currently is doing will be printed to the console
				(default = False)
	
	returns
	data			-	a list with a dict for every trial (see above)
	"""

	# # # # #
	# debug mode
	
	if debug:
		def message(msg):
			print(msg)
	else:
		def message(msg):
			pass
		
	
	# # # # #
	# file handling
	
	# check if the file exists
	if os.path.isfile(filename):
		# open file
		message("opening file '%s'" % filename)
		f = open(filename, 'r')
	# raise exception if the file does not exist
	else:
		raise Exception("Error in read_edf: file '%s' does not exist" % filename)
	
	# read file contents
	message("reading file '%s'" % filename)
	raw = f.readlines()
	
	# close file
	message("closing file '%s'" % filename)
	f.close()

	
	# # # # #
	# parse lines
	
	# variables
	data = []
	x = []
	y = []
	size = []
	time = []
	trackertime = []
	events = {'Sfix':[],'Ssac':[],'Sblk':[],'Efix':[],'Esac':[],'Eblk':[],'msg':[]}
	starttime = 0
	started = False
	trialend = False
	finalline = raw[-1]
	
	# loop through all lines
	for line in raw:
		
		# check if trial has already started
		if started:
			# only check for stop if there is one
			if stop != None:
				if stop in line:
					started = False
					trialend = True
			# check for new start otherwise
			else:
				if (start in line) or (line == finalline):
					started = True
					trialend = True
			
			# # # # #
			# trial ending
			
			if trialend:
				message("trialend %d; %d samples found" % (len(data),len(x)))
				# trial dict
				trial = {}
				trial['x'] = numpy.array(x)
				trial['y'] = numpy.array(y)
				trial['size'] = numpy.array(size)
				trial['time'] = numpy.array(time)
				trial['trackertime'] = numpy.array(trackertime)
				trial['events'] = copy.deepcopy(events)
				# add trial to data
				data.append(trial)
				# reset stuff
				x = []
				y = []
				size = []
				time = []
				trackertime = []
				events = {'Sfix':[],'Ssac':[],'Sblk':[],'Efix':[],'Esac':[],'Eblk':[],'msg':[]}
				trialend = False
				
		# check if the current line contains start message
		else:
			if start in line:
				message("trialstart %d" % len(data))
				# set started to True
				started = True
				# find starting time
				starttime = int(line[line.find('\t')+1:line.find(' ')])
		
		# # # # #
		# parse line
		
		if started:
			# message lines will start with MSG, followed by a tab, then a
			# timestamp, a space, and finally the message, e.g.:
			#	"MSG\t12345 something of importance here"
			if line[0:3] == "MSG":
				ms = line.find(" ") # message start
				t = int(line[4:ms]) # time
				m = line[ms+1:] # message
				events['msg'].append([t,m])
	
			# EDF event lines are constructed of 9 characters, followed by
			# tab separated values; these values MAY CONTAIN SPACES, but
			# these spaces are ignored by float() (thank you Python!)
					
			# fixation start
			elif line[0:6] == "SFIX L":
				message("LEFT fixation start")
				l = line[9:]
				events['Sfix'].append(int(l))
			# fixation end
			elif line[0:6] == "EFIX L":
				message("LEFT fixation end")
				l = line[9:]
				l = l.split('\t')
				st = int(l[0]) # starting time
				et = int(l[1]) # ending time
				dur = int(l[2]) # duration
				sx = replace_missing(l[3], missing=missing) # x position
				sy = replace_missing(l[4], missing=missing) # y position
				events['Efix'].append([st, et, dur, sx, sy])
			# saccade start
			elif line[0:7] == 'SSACC L':
				message("LEFT saccade start")
				l = line[9:]
				events['Ssac'].append(int(l))
			# saccade end
			elif line[0:7] == "ESACC L":
				message("LEFT saccade end")
				l = line[9:]
				l = l.split('\t')
				st = int(l[0]) # starting time
				et = int(l[1]) # endint time
				dur = int(l[2]) # duration
				sx = replace_missing(l[3], missing=missing) # start x position
				sy = replace_missing(l[4], missing=missing) # start y position
				ex = replace_missing(l[5], missing=missing) # end x position
				ey = replace_missing(l[6], missing=missing) # end y position
				events['Esac'].append([st, et, dur, sx, sy, ex, ey])
			# blink start
			elif line[0:6] == "SBLINK":
				message("blink start")
				l = line[9:]
				events['Sblk'].append(int(l))
			# blink end
			elif line[0:6] == "EBLINK":
				message("blink end")
				l = line[9:]
				l = l.split('\t')
				st = int(l[0])
				et = int(l[1])
				dur = int(l[2])
				events['Eblk'].append([st,et,dur])
			
			# regular lines will contain tab separated values, beginning with
			# a timestamp, follwed by the values that were asked to be stored
			# in the EDF and a mysterious '...'. Usually, this comes down to
			# timestamp, x, y, pupilsize, ...
			# e.g.: "985288\t  504.6\t  368.2\t 4933.0\t..."
			# NOTE: these values MAY CONTAIN SPACES, but these spaces are
			# ignored by float() (thank you Python!)
			else:
				# see if current line contains relevant data
				try:
					# split by tab
					l = line.split('\t')
					# if first entry is a timestamp, this should work
					int(l[0])
				except:
					message("line '%s' could not be parsed" % line)
					continue # skip this line

				# check missing
				if float(l[3]) == 0.0:
					l[1] = 0.0
					l[2] = 0.0
				
				# extract data
				x.append(float(l[1]))
				y.append(float(l[2]))
				size.append(float(l[3]))
				time.append(int(l[0])-starttime)
				trackertime.append(int(l[0]))
	
	
	# # # # #
	# return
	
	return data


# DEBUG #
if __name__ == "__main__":
	# start: MSG	3120773 TRIALNR 8 TARX 662 TARY 643 DISX 771 DISY 233 CSTPE 0 REINFORCE 0
	# stop: MSG	3118572 TRIALNR END 7
	data = read_edf('1.asc', "TRIALNR", stop="TRIALNR END", debug=False)
	
	x = numpy.zeros(len(data[0]['x'])*1.5)
	y = numpy.zeros(len(data[0]['y'])*1.5)
	size = y = numpy.zeros(len(data[0]['size'])*1.5)
	
	for i in range(len(data)):
		x[:len(data[i]['x'])] = x[:len(data[i]['x'])] + data[i]['x']
		y[:len(data[i]['y'])] = y[:len(data[i]['y'])] + data[i]['y']
		y[:len(data[i]['size'])] = y[:len(data[i]['size'])] + data[i]['size']
	x = x/len(data)
	y = y/len(data)
	size = size/len(data)
	
	from matplotlib import pyplot
	pyplot.figure()
	pyplot.plot(data[0]['time'],data[0]['x'],'r')
	pyplot.plot(data[0]['time'],data[0]['y'],'g')
	pyplot.plot(data[0]['time'],data[0]['size'],'b')
	
	pyplot.figure()
	pyplot.plot(size,'b')
	
	pyplot.figure()
	pyplot.plot(x,y,'ko')
# # # # #
    
    # -*- coding: utf-8 -*-
#
# This file is part of PyGaze - the open-source toolbox for eye tracking
#
#	PyGazeAnalyser is a Python module for easily analysing eye-tracking data
#	Copyright (C) 2014  Edwin S. Dalmaijer
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>

# Gaze Plotter
#
# Produces different kinds of plots that are generally used in eye movement
# research, e.g. heatmaps, scanpaths, and fixation locations as overlays of
# images.
#
# version 2 (02 Jul 2014)

__author__ = "Edwin Dalmaijer"

# native
import os
# external
import numpy
import matplotlib
from matplotlib import pyplot, image


# # # # #
# LOOK

# COLOURS
# all colours are from the Tango colourmap, see:
# http://tango.freedesktop.org/Tango_Icon_Theme_Guidelines#Color_Palette
COLS = {	"butter": [	'#fce94f',
					'#edd400',
					'#c4a000'],
		"orange": [	'#fcaf3e',
					'#f57900',
					'#ce5c00'],
		"chocolate": [	'#e9b96e',
					'#c17d11',
					'#8f5902'],
		"chameleon": [	'#8ae234',
					'#73d216',
					'#4e9a06'],
		"skyblue": [	'#729fcf',
					'#3465a4',
					'#204a87'],
		"plum": 	[	'#ad7fa8',
					'#75507b',
					'#5c3566'],
		"scarletred":[	'#ef2929',
					'#cc0000',
					'#a40000'],
		"aluminium": [	'#eeeeec',
					'#d3d7cf',
					'#babdb6',
					'#888a85',
					'#555753',
					'#2e3436'],
		}
# FONT
FONT = {	'family': 'Ubuntu',
		'size': 12}
matplotlib.rc('font', **FONT)


# # # # #
# FUNCTIONS

def draw_fixations(fixations, dispsize, imagefile=None, durationsize=True, durationcolour=True, alpha=0.5, savefilename=None):
	
	"""Draws circles on the fixation locations, optionally on top of an image,
	with optional weigthing of the duration for circle size and colour
	
	arguments
	
	fixations		-	a list of fixation ending events from a single trial,
					as produced by edfreader.read_edf, e.g.
					edfdata[trialnr]['events']['Efix']
	dispsize		-	tuple or list indicating the size of the display,
					e.g. (1024,768)
	
	keyword arguments
	
	imagefile		-	full path to an image file over which the heatmap
					is to be laid, or None for no image; NOTE: the image
					may be smaller than the display size, the function
					assumes that the image was presented at the centre of
					the display (default = None)
	durationsize	-	Boolean indicating whether the fixation duration is
					to be taken into account as a weight for the circle
					size; longer duration = bigger (default = True)
	durationcolour	-	Boolean indicating whether the fixation duration is
					to be taken into account as a weight for the circle
					colour; longer duration = hotter (default = True)
	alpha		-	float between 0 and 1, indicating the transparancy of
					the heatmap, where 0 is completely transparant and 1
					is completely untransparant (default = 0.5)
	savefilename	-	full path to the file in which the heatmap should be
					saved, or None to not save the file (default = None)
	
	returns
	
	fig			-	a matplotlib.pyplot Figure instance, containing the
					fixations
	"""

	# FIXATIONS
	fix = parse_fixations(fixations)
	
	# IMAGE
	fig, ax = draw_display(dispsize, imagefile=imagefile)

	# CIRCLES
	# duration weigths
	if durationsize:
		siz = 200 * (fix['dur']/30.0)
	else:
		siz = 1 * numpy.median(fix['dur']/30.0)
	if durationcolour:
		col = fix['dur']
	else:
		col = COLS['chameleon'][2]
	# draw circles
	#ax.scatter(fix['x'],fix['y'], s=siz, c=col, marker='o', cmap='jet', alpha=alpha, edgecolors='face')
	
	graf=ax.scatter(fix['x'],fix['y'], s=siz, c=col, cmap='jet', alpha=alpha, edgecolors='face')
	#graf.set_facecolor('none')
	
    # FINISH PLOT
	# invert the y axis, as (0,0) is top left on a display
	ax.invert_yaxis()
	# save the figure if a file name was provided
	if savefilename != None:
		fig.savefig(savefilename)
	
	#return fig


def draw_heatmap(fixations, dispsize, imagefile=None, durationweight=True, alpha=0.5, savefilename=None):
	
	"""Draws a heatmap of the provided fixations, optionally drawn over an
	image, and optionally allocating more weight to fixations with a higher
	duration.
	
	arguments
	
	fixations		-	a list of fixation ending events from a single trial,
					as produced by edfreader.read_edf, e.g.
					edfdata[trialnr]['events']['Efix']
	dispsize		-	tuple or list indicating the size of the display,
					e.g. (1024,768)
	
	keyword arguments
	
	imagefile		-	full path to an image file over which the heatmap
					is to be laid, or None for no image; NOTE: the image
					may be smaller than the display size, the function
					assumes that the image was presented at the centre of
					the display (default = None)
	durationweight	-	Boolean indicating whether the fixation duration is
					to be taken into account as a weight for the heatmap
					intensity; longer duration = hotter (default = True)
	alpha		-	float between 0 and 1, indicating the transparancy of
					the heatmap, where 0 is completely transparant and 1
					is completely untransparant (default = 0.5)
	savefilename	-	full path to the file in which the heatmap should be
					saved, or None to not save the file (default = None)
	
	returns
	
	fig			-	a matplotlib.pyplot Figure instance, containing the
					heatmap
	"""

	# FIXATIONS
	fix = parse_fixations(fixations)
	
	# IMAGE
	fig, ax = draw_display(dispsize, imagefile=imagefile)

	# HEATMAP
	# Gaussian
	gwh = 200
	gsdwh = gwh/6
	gaus = gaussian(gwh,gsdwh)
	# matrix of zeroes
	strt = gwh/2
	heatmapsize = dispsize[1] + 2*strt, dispsize[0] + 2*strt
	
	heatmap = numpy.zeros([int(heatmapsize[0]),int(heatmapsize[1])], dtype=float)
	# create heatmap
	for i in range(0,len(fix['dur'])):
		# get x and y coordinates
		#x and y - indexes of heatmap array. must be integers
		x = strt + int(fix['x'][i]) - int(gwh/2)
		y = strt + int(fix['y'][i]) - int(gwh/2)
		# correct Gaussian size if either coordinate falls outside of
		# display boundaries
		if (not 0 < x < dispsize[0]) or (not 0 < y < dispsize[1]):
			hadj=[0,gwh];vadj=[0,gwh]
			if 0 > x:
				hadj[0] = abs(x)
				x = 0
			elif dispsize[0] < x:
				hadj[1] = gwh - int(x-dispsize[0])
			if 0 > y:
				vadj[0] = abs(y)
				y = 0
			elif dispsize[1] < y:
				vadj[1] = gwh - int(y-dispsize[1])
			# add adjusted Gaussian to the current heatmap
			try:
				heatmap[y:y+vadj[1],x:x+hadj[1]] += gaus[vadj[0]:vadj[1],hadj[0]:hadj[1]] * fix['dur'][i]
			except:
				# fixation was probably outside of display
				pass
		else:				
			# add Gaussian to the current heatmap
			heatmap[int(y):int(y+gwh),int(x):int(x+gwh)] += gaus * fix['dur'][i]
	# resize heatmap
	heatmap = heatmap[int(strt):int(dispsize[1]+strt),int(strt):int(dispsize[0]+strt)]
	# remove zeros
	lowbound = numpy.mean(heatmap[heatmap>0])
	heatmap[heatmap<lowbound] = numpy.NaN
	# draw heatmap on top of image
	ax.imshow(heatmap, cmap='jet', alpha=alpha)

	# FINISH PLOT
	# invert the y axis, as (0,0) is top left on a display
	ax.invert_yaxis()
	# save the figure if a file name was provided
	if savefilename != None:
		fig.savefig(savefilename)
	
	#return fig


def draw_raw(x, y, dispsize, imagefile=None, savefilename=None):
	
	"""Draws the raw x and y data
	
	arguments
	
	x			-	a list of x coordinates of all samples that are to
					be plotted
	y			-	a list of y coordinates of all samples that are to
					be plotted
	dispsize		-	tuple or list indicating the size of the display,
					e.g. (1024,768)
	
	keyword arguments
	
	imagefile		-	full path to an image file over which the heatmap
					is to be laid, or None for no image; NOTE: the image
					may be smaller than the display size, the function
					assumes that the image was presented at the centre of
					the display (default = None)
	savefilename	-	full path to the file in which the heatmap should be
					saved, or None to not save the file (default = None)
	
	returns
	
	fig			-	a matplotlib.pyplot Figure instance, containing the
					fixations
	"""
	
	# image
	fig, ax = draw_display(dispsize, imagefile=imagefile)

	# plot raw data points
	ax.plot(x, y, 'o', color=COLS['aluminium'][0], markeredgecolor=COLS['aluminium'][5])

	# invert the y axis, as (0,0) is top left on a display
	ax.invert_yaxis()
	# save the figure if a file name was provided
	if savefilename != None:
		fig.savefig(savefilename)
	
	#return fig


def draw_scanpath(fixations, saccades, dispsize, imagefile=None, alpha=0.5, savefilename=None):
	
	"""Draws a scanpath: a series of arrows between numbered fixations,
	optionally drawn over an image

	arguments
	
	fixations		-	a list of fixation ending events from a single trial,
					as produced by edfreader.read_edf, e.g.
					edfdata[trialnr]['events']['Efix']
	saccades		-	a list of saccade ending events from a single trial,
					as produced by edfreader.read_edf, e.g.
					edfdata[trialnr]['events']['Esac']
	dispsize		-	tuple or list indicating the size of the display,
					e.g. (1024,768)
	
	keyword arguments
	
	imagefile		-	full path to an image file over which the heatmap
					is to be laid, or None for no image; NOTE: the image
					may be smaller than the display size, the function
					assumes that the image was presented at the centre of
					the display (default = None)
	alpha		-	float between 0 and 1, indicating the transparancy of
					the heatmap, where 0 is completely transparant and 1
					is completely untransparant (default = 0.5)
	savefilename	-	full path to the file in which the heatmap should be
					saved, or None to not save the file (default = None)
	
	returns
	
	fig			-	a matplotlib.pyplot Figure instance, containing the
					heatmap
	"""
	
	# image
	fig, ax = draw_display(dispsize, imagefile=imagefile)

	# FIXATIONS
	# parse fixations
	fix = parse_fixations(fixations)
	# draw fixations
	ax.scatter(fix['x'],fix['y'], s=(1 * fix['dur'] / 30.0), c=COLS['chameleon'][2], marker='o', cmap='jet', alpha=alpha, edgecolors='none')
	# draw annotations (fixation numbers)
	for i in range(len(fixations)):
		ax.annotate(str(i+1), (fix['x'][i],fix['y'][i]), color=COLS['aluminium'][5], alpha=1, horizontalalignment='center', verticalalignment='center', multialignment='center')

	# SACCADES
	if saccades:
		# loop through all saccades
		for st, et, dur, sx, sy, ex, ey in saccades:
			# draw an arrow between every saccade start and ending
			ax.arrow(sx, sy, ex-sx, ey-sy, alpha=alpha, fc=COLS['aluminium'][0], ec=COLS['aluminium'][5], fill=True, shape='full', width=10, head_width=20, head_starts_at_zero=False, overhang=0)

	# invert the y axis, as (0,0) is top left on a display
	ax.invert_yaxis()
	# save the figure if a file name was provided
	if savefilename != None:
		fig.savefig(savefilename)
	
	#return fig


# # # # #
# HELPER FUNCTIONS


def draw_display(dispsize, imagefile=None):
	
	"""Returns a matplotlib.pyplot Figure and its axes, with a size of
	dispsize, a black background colour, and optionally with an image drawn
	onto it
	
	arguments
	
	dispsize		-	tuple or list indicating the size of the display,
					e.g. (1024,768)
	
	keyword arguments
	
	imagefile		-	full path to an image file over which the heatmap
					is to be laid, or None for no image; NOTE: the image
					may be smaller than the display size, the function
					assumes that the image was presented at the centre of
					the display (default = None)
	
	returns
	fig, ax		-	matplotlib.pyplot Figure and its axes: field of zeros
					with a size of dispsize, and an image drawn onto it
					if an imagefile was passed
	"""
	
	# construct screen (black background)
	_, ext = os.path.splitext(imagefile)
	ext = ext.lower()
	data_type = 'float32' if ext == '.png' else 'uint8'
	screen = numpy.zeros((dispsize[1],dispsize[0],3), dtype=data_type)
	# if an image location has been passed, draw the image
	if imagefile != None:
		# check if the path to the image exists
		if not os.path.isfile(imagefile):
			raise Exception("ERROR in draw_display: imagefile not found at '%s'" % imagefile)
		# load image
		img = image.imread(imagefile)
		# flip image over the horizontal axis
		# (do not do so on Windows, as the image appears to be loaded with
		# the correct side up there; what's up with that? :/)
		#if not os.name == 'nt': #Dos lineas siguientes comentadas por Tino
		#	img = numpy.flipud(img)
		# width and height of the image
		w, h = len(img[0]), len(img)
		# x and y position of the image on the display
		x = dispsize[0]/2 - w/2
		#print("This is x:", 100)
		y = dispsize[1]/2 - h/2
		# draw the image on the screen
		screen[int(y):int(y+h),int(x):int(x+w),:] += img
	# dots per inch
	dpi = 100.0
	# determine the figure size in inches
	figsize = (dispsize[0]/dpi, dispsize[1]/dpi)
	# create a figure
	fig = pyplot.figure(figsize=figsize, dpi=dpi, frameon=False)
	ax = pyplot.Axes(fig, [0,0,1,1])
	ax.set_axis_off()
	fig.add_axes(ax)
	# plot display
	ax.axis([0,dispsize[0],0,dispsize[1]])
	ax.imshow(screen)#, origin='upper')
	
	return fig, ax


def gaussian(x, sx, y=None, sy=None):
	
	"""Returns an array of numpy arrays (a matrix) containing values between
	1 and 0 in a 2D Gaussian distribution
	
	arguments
	x		-- width in pixels
	sx		-- width standard deviation
	
	keyword argments
	y		-- height in pixels (default = x)
	sy		-- height standard deviation (default = sx)
	"""
	
	# square Gaussian if only x values are passed
	if y == None:
		y = x
	if sy == None:
		sy = sx
	# centers	
	xo = x/2
	yo = y/2
	# matrix of zeros
	M = numpy.zeros([y,x],dtype=float)
	# gaussian matrix
	for i in range(x):
		for j in range(y):
			M[j,i] = numpy.exp(-1.0 * (((float(i)-xo)**2/(2*sx*sx)) + ((float(j)-yo)**2/(2*sy*sy)) ) )

	return M


def parse_fixations(fixations):
	
	"""Returns all relevant data from a list of fixation ending events
	
	arguments
	
	fixations		-	a list of fixation ending events from a single trial,
					as produced by edfreader.read_edf, e.g.
					edfdata[trialnr]['events']['Efix']

	returns
	
	fix		-	a dict with three keys: 'x', 'y', and 'dur' (each contain
				a numpy array) for the x and y coordinates and duration of
				each fixation
	"""
	
	# empty arrays to contain fixation coordinates
	fix = {	'x':numpy.zeros(len(fixations)),
			'y':numpy.zeros(len(fixations)),
			'dur':numpy.zeros(len(fixations))}
	# get all fixation coordinates
	for fixnr in range(len( fixations)):
		stime, etime, dur, ex, ey = fixations[fixnr]
		fix['x'][fixnr] = ex
		fix['y'][fixnr] = ey
		fix['dur'][fixnr] = dur
	
	return fix
