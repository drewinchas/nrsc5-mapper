#!/opt/homebrew/bin/python3
#
# python version 3.11
#
import argparse, sys, shutil, os, signal, re, datetime
from subprocess import Popen, PIPE, STDOUT
from os import listdir
from time import sleep
from dateutil import tz

# Taken from nrsc5-dui.py
from PIL import Image, ImageFont, ImageDraw, __version__

print('Using Pillow v'+__version__)

if (int(__version__[0]) < 9):
    imgLANCZOS = Image.LANCZOS
else:
    imgLANCZOS = Image.Resampling.LANCZOS


# Setup the NRC5 log file
nrsc5log = open("nrsc5.log", "w")

# Specify the working directories
aasDir = './aas'
mapDir = './map'
resDir = './res'
mapFile = os.path.join(resDir, 'map.png')

# Setup some data structures. Taken from nrsc5-dui.py
mapData = {
    "mapMode"       : 1,
    "mapTiles"      : [[0,0,0],[0,0,0],[0,0,0]],
    "mapComplete"   : False,
    "weatherTime"   : 0,
    "weatherPos"    : [0,0,0,0],
    "weatherNow"    : "",
    "weatherID"     : "",
    "viewerConfig"  : {
        "mode"           : 1,
        "animate"        : False,
        "scale"          : True,
        "windowPos"      : (0,0),
        "windowSize"     : (764,632),
        "animationSpeed" : 0.5
    }
}

# Setup the NRSC5 output directories (for maps)
try:
    os.mkdir(aasDir)
except:
    pass

try:
    os.mkdir(mapDir)
except:
    pass


# Some time conversion routines. Taken from nrsc5-dui.py
def dtToTs(dt):
    # convert datetime to timestamp
    return int((dt - datetime.datetime(1970, 1, 1, tzinfo=tz.tzutc())).total_seconds())

def tsToDt(ts):
    # convert timestamp to datetime
    return datetime.datetime.utcfromtimestamp(ts)
    
def mkTimestamp(t, size, pos):
    # create a timestamp image to overlay on the weathermap
    x,y   = pos
    text  = "{:04g}-{:02g}-{:02g} {:02g}:{:02g}".format(t.year, t.month, t.day, t.hour, t.minute)   # format timestamp
    imgTS = Image.new("RGBA", size, (0,0,0,0))                                                      # create a blank image
    draw  = ImageDraw.Draw(imgTS)                                                                   # the drawing object
    font  = ImageFont.truetype(os.path.join(resDir,"DejaVuSansMono.ttf"), 24)                       # DejaVu Sans Mono 24pt font
    draw.rectangle((x,y, x+231,y+25), outline="black", fill=(128,128,128,96))                       # draw a box around the text
    draw.text((x+3,y), text, fill="black", font=font)                                               # draw the text
    return imgTS                                                                                    # return the image

# Get Lat and Lon from DWRI file
def getMapPoints(fileName):
    f = open(os.path.join(aasDir, fileName), 'r')
    linesDict = {}
    sleep(1) # Gotta wait until the file has been completely written... Learned this the hard way.
    for line in f:
        pairs = line.strip().split('=') # split around the = sign
        if len(pairs) > 1: # we have the = sign in there
            linesDict[pairs[0]] = pairs[1]
            
    areaId = linesDict['DWR_Area_ID'].strip('"')
    coords = linesDict['Coordinates'].strip().split(';')
    
    # Get north and west bounds
    bounds = coords[0].strip('"').strip('(').strip(')').split(',')
    north = float(bounds[0])
    west = float(bounds[1])
    
    # Get south and east bounds
    bounds = coords[1].strip('"').strip('(').strip(')').split(',')
    south = float(bounds[0])
    east = float(bounds[1])
    
    # Delete the file from disk (we don't need it anymore)
    os.remove(os.path.join(aasDir, fileName))
    return(areaId, north, west, south, east)

# Convert to MapArea pixel Coordinates. Taken from nrsc5-dui.py
def getMapArea(lat1, lon1, lat2, lon2):
    from math import asinh, tan, radians
    
    # get pixel coordinates from latitude and longitude
    # calculations taken from https://github.com/KYDronePilot/hdfm
    top  = asinh(tan(radians(52.482780)))
    lat1 = top - asinh(tan(radians(lat1)))
    lat2 = top - asinh(tan(radians(lat2)))
    x1   = (lon1 + 130.781250) * 7162 / 39.34135
    x2   = (lon2 + 130.781250) * 7162 / 39.34135
    y1   = lat1 * 3565 / (top - asinh(tan(radians(38.898))))
    y2   = lat2 * 3565 / (top - asinh(tan(radians(38.898))))
    return (int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2)))

# Create the BaseMap. Taken from nrsc5-dui.py
def makeBaseMap(id, pos):
    mapPath = os.path.join(mapDir, "BaseMap_" + id + ".png")
    # get map path
    if (os.path.isfile(mapFile)):
        if (os.path.isfile(mapPath) == False):
        # check if the map has already been created for this location
            print("Creating new map: " + mapPath)
            px = getMapArea(*pos)
            # convert map locations to pixel coordinates
            mapImg = Image.open(mapFile).crop(px)
            # open the full map and crop it to the coordinates
            mapImg.save(mapPath)
            # save the cropped map to disk for later use
            print("Finished creating map")
    else:
        print("Error map file not found: " + mapFile, True)
        mapImg = Image.new("RGBA", (pos[2]-pos[1], pos[3]-pos[1]), "white")
        # if the full map is not available, use a blank image
        mapImg.save(mapPath)

# Force it to wait a second before we attempt to process
def makeWeatherMap(fileName):
    sleep(1)
    processWeatherOverlay(fileName)


# Process the WeatherOverlay. Taken from nrsc5-dui.py
def processWeatherOverlay(fileName):
    r = re.compile("^[\d]+_DWRO_(.*)_.*_([\d]{4})([\d]{2})([\d]{2})_([\d]{2})([\d]{2})_([0-9A-Fa-f]+)\..*$")                    # match file name
    m = r.match(fileName)
    
    if (m):
        # get time from map tile and convert to local time
        dt = datetime.datetime(int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6)), tzinfo=tz.tzutc())
        t  = dt.astimezone(tz.tzlocal())                                                            # local time
        ts = dtToTs(dt)                                                                             # unix timestamp (utc)
        id = mapData["weatherID"]
            
        if (m.group(1) != id):
            if (id == ""):
                print("Received weather overlay before metadata, ignoring...");
            else:
                print("Received weather overlay with the wrong ID: " + m.group(1) + " (wanted " + id +")")
            return
            
        if (mapData["weatherTime"] == ts):
            try:
                os.remove(os.path.join(aasDir, fileName))                                           # delete this tile, it's not needed
            except:
                pass
            return                  # no need to recreate the map if it hasn't changed
            
        print("Got Weather Overlay")
            
        mapData["weatherTime"] = ts                                                            # store time for current overlay
        wxOlPath  = os.path.join(mapDir,"WeatherOverlay_{:s}_{:}.png".format(id, ts))
        wxMapPath = os.path.join(mapDir,"WeatherMap_{:s}_{:}.png".format(id, ts))
            
        # move new overlay to map directory
        try:
            if(os.path.exists(wxOlPath)): os.remove(wxOlPath)                                       # delete old image if it exists (only necessary on windows)
            fs = open(os.path.join(aasDir, fileName), 'rb')
            fd = open(wxOlPath, 'wb')
            fd.write(fs.read())
            os.remove(os.path.join(aasDir, fileName))
            # move and rename map tile
        except:
            print("Error moving weather overlay", True)
            mapData["weatherTime"] = 0
                
        # create weather map
        try:
            mapPath = os.path.join(mapDir, "BaseMap_" + id + ".png")                                # get path to base map
            if (os.path.isfile(mapPath) == False):                                                  # make sure base map exists
                makeBaseMap(mapData["weatherID"], mapData["weatherPos"])             # create base map if it doesn't exist
                
            imgMap   = Image.open(mapPath).convert("RGBA")                                          # open map image
            posTS    = (imgMap.size[0]-235, imgMap.size[1]-29)                                      # calculate position to put timestamp (bottom right)
            imgTS    = mkTimestamp(t, imgMap.size, posTS)                                      # create timestamp
            imgRadar = Image.open(wxOlPath).convert("RGBA")                                         # open radar overlay
            imgRadar = imgRadar.resize(imgMap.size, imgLANCZOS)                                  # resize radar overlay to fit the map
            imgMap   = Image.alpha_composite(imgMap, imgRadar)                                      # overlay radar image on map
            imgMap   = Image.alpha_composite(imgMap, imgTS)                                         # overlay timestamp
            imgMap.save(wxMapPath)                                                                  # save weather map
            os.remove(wxOlPath)                                                                    # remove overlay image
            os.remove(mapPath)
                # remove BaseMap
            mapData["weatherNow"] = wxMapPath
                
            # display on map page
            #if (self.radMapWeather.get_active()):
            #    img_size = min(self.alignmentMap.get_allocated_height(), self.alignmentMap.get_allocated_width()) - 12
            #    imgMap = imgMap.resize((img_size, img_size), imgLANCZOS)                         # scale map to fit window
            #    self.imgMap.set_from_pixbuf(imgToPixbuf(imgMap))                                    # convert image to pixbuf and display
                
            #self.proccessWeatherMaps()                                                              # get rid of old maps and add new ones to the list
            #if (self.mapViewer is not None): self.mapViewer.updated(1)                              # notify map viwerer if it's open
                    
        except:
            print("Error creating weather map", True)
            mapData["weatherTime"] = 0

#
# MAIN Routine
#



# Use argparse to parse commandline arguments in order to perform specific actions. Reference: https://www.geeksforgeeks.org/python-how-to-parse-command-line-options/
cmdparser = argparse.ArgumentParser(description ='nsrc5-mapper - Download (and Assemble) traffic and weather maps transmitted via NRSC-5 (HD Radio)')
# Get rtltcp-host option for NRSC5
cmdparser.add_argument('-H', dest='tcpHost', action='store', help = 'rtltcp-host:port')
# Get the aasDir, if the user wants to override
cmdparser.add_argument('--dump-aas-files', dest='aasDir', action='store', help = 'Specify (override) aas directory (aasDir)')
# Get the mapDir, if the user wants to override
cmdparser.add_argument('-M', dest='mapDir', action='store', help = 'Specify (override) the map output direectory (mapDir)')
# Get the frequency for NRSC5
cmdparser.add_argument('frequency', type=str, help='frequency')
# Get the program for NRSC5
cmdparser.add_argument('program', type=str, help='program number (0 - 3)')


myargs = cmdparser.parse_args()
nrsc5args = ['nrsc5']
if myargs.tcpHost:
    nrsc5args.append('-H')
    nrsc5args.append(myargs.tcpHost)
if myargs.aasDir:
    aasDir = myargs.aasDir
if myargs.mapDir:
    mapDir = myargs.mapDir

nrsc5args.append('--dump-aas-files')
nrsc5args.append(aasDir)
nrsc5args.append(myargs.frequency)
nrsc5args.append(myargs.program)

# Launch nrsc5 in the background
nrsc5PID = Popen(nrsc5args, shell=False)
print(nrsc5PID.pid)

while True:
    aasfiles = listdir(aasDir)
    for fn in aasfiles:
        # If we find a weather index file, let's make a basemap and set some values
        if 'DWRI'.lower() in fn.lower():
            pts = getMapPoints(fn)
            mapData["weatherID"] = pts[0]
            mapData["weatherPos"] = [pts[1], pts[2], pts[3], pts[4]]
            print(pts)
            #makeBaseMap(mapData["weatherID"], mapData["weatherPos"])
        # If we find a weather radar image, let's make a radar map
        if 'DWRO'.lower() in fn.lower():
            print(fn)
            makeWeatherMap(fn)
            
        
            
            




