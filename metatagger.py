import configparser
import os
import sys
import ffmpeg
import datetime
import time
import json
import re
import xml.etree.ElementTree as ET
from moviepy import VideoFileClip
from xml.dom import minidom

if os.name == 'nt':
    delimeter = '\\'
else:
    delimeter = '/'

scriptPath = os.path.realpath(os.path.dirname(__file__))
config = configparser.ConfigParser()
config.read(scriptPath + delimeter + 'config.ini')

directory = config['metatagger']['output subdirectory']

cwd = os.getcwd()

def selectFile(k):
    fileSelection = input(">:")
    try:
        fileSelection = int(fileSelection)
    except ValueError:
        print("Enter a Number Between 1 and "+str(k-1)+":")
        fileSelection = input(">:")
    while fileSelection >= int(k):
        print("Enter a Number Between 1 and "+str(k-1)+":")
        fileSelection = input(">:")
        try:
            fileSelection = int(fileSelection)
        except ValueError:
            fileSelection = k
    return fileSelection
    
def selectJSON(path):
    dirContents = os.scandir(path)
    dirDict = {}
    k = 1
    for entry in dirContents:
        if entry.name[-4:].lower() in 'json':
            dirDict[k] = entry.name
            print(str(k)+": "+entry.name)
            k = k + 1
    fileSelection = selectFile(k)
    print("\nJSON FILE SELECTED")
    print(path+dirDict[fileSelection])
    cont = input("\nContinue with this file? (Y/N) >:")
    yn = ['y','Y','Yes','YES','yes','N','n','No','NO','no']
    yes = ['y','Y','Yes','YES','yes']
    no = ['N','n','No','NO','no']
    while cont not in yn:
        print("INVALID ENTRY")
        cont = input("Continue with this file? (Y/N) >:")
    while cont in no:
        print("Enter a Number Between 1 and "+str(k-1)+":")
        fileSelection = selectFile(k)
        print("FILE SELECTED")
        print(dirDict[fileSelection])
        cont = input("\nContinue with this file? (Y/N) >:")
    print("CONFIRMED!")
    return dirDict[fileSelection]

def selectDirectory(delimeter=delimeter):
    print("Enter the directory path to scan")
    workingDir = os.getcwd()
    print("Press Enter to use "+workingDir)
    path = input(">:")
    if path == "":
        path = workingDir
    if path[-1] != delimeter:
        path = path + delimeter
    print("Selected Directory: "+path)
    return path

def editMetadata(filename,outputPath,metadata,outputFile=None):
    if outputFile == None:
        outputFile = outputPath + delimeter + filename.split(delimeter)[-1]
    
    try:
        (
            ffmpeg
            .input(filename)
            .output(
                outputFile, 
                c='copy', 
                loglevel="verbose",
                **{
                    'metadata:g:0':"title="+metadata['description'],
                    'metadata:g:1':"date="+metadata['date'],
                    'metadata:g:2':"genre="+metadata['tags'],
                    'metadata:g:3':"network="+metadata['network'],
                    'metadata:g:4':"synopsis="+metadata['Description']+'\n'+metadata['Location']+'\n'+metadata['Tape ID'],
                    'metadata:g:5':"episode_id="+metadata['clip'],
                    'metadata:g:6':"comment="+metadata['Location']+'\n'+metadata['Description'],
                }
            )
            .run(capture_stdout=True, capture_stderr=True)
    )
    except ffmpeg.Error as e:
        print(e.stderr)

def createMetadata(filename,outputPath,metadata,outputFile):
    outputFile = os.path.join(outputPath,outputFile)
    #print(filename)
    #print(outputFile)
    #print('')

    try:
        #print("Processing metadata with ffmpeg")
        (
            ffmpeg
            .input(filename)
            .output(
                outputFile, 
                c='copy', 
                loglevel="verbose",
                **{
                    'metadata:g:0':"title="+metadata['Title'],
                    'metadata:g:1':"date="+metadata['Air Date'],
                    'metadata:g:2':"genre="+metadata['Tags'],
                    'metadata:g:3':"network="+metadata['Network/Station'],
                    'metadata:g:4':"synopsis="+metadata['Description']+'\n'+metadata['Location']+'\n'+metadata['Tape ID'],
                    'metadata:g:5':"episode_id="+str(metadata['Frame Range'][0]),
                    'metadata:g:6':"comment="+metadata['Location']+'\n'+metadata['Description'],
                }
            )
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        print(e.stderr)
    
def tagFiles(JSONFile=None, workingDirectory=None, directory=directory):
    if workingDirectory == None:
        workingDirectory = selectDirectory()
    if JSONFile == None:
        JSONFile = selectJSON(workingDirectory)
    j = open(JSONFile,)
    jsonData = json.load(j)

    destinationDirectory = workingDirectory + directory
    print(destinationDirectory)
    if os.path.exists(destinationDirectory) != True:
        print("_metadata directory does not exist, creating directory...")
        try:
            os.makedirs(destinationDirectory)
        except Exception as e:
            print("ERROR: Could not create directory\n"+str(e))

    for d in jsonData:
        if d['Folder'] == workingDirectory.split(delimeter)[-2]:
            print(d['Filename'])
            editMetadata(d['Filename'],destinationDirectory,{'description':d['Description'],'date':d['Air Date'],'tags':d['Tags'],'network':d['Network/Station'],'tapeID':d['Tape ID'],'clip':str(d['Clip Number']),'location':d['Location']})
        else:
            print(d['Folder'])
            print(workingDirectory.split(delimeter)[-2])
            print("Directories do not match, skipping...")
            

def create_xml_from_json(data):
    root = ET.Element('movie')

    # Iterate over the dictionary items and create XML elements
    for key, value in data.items():
        if key == 'Air Date':
            year = ET.SubElement(root, 'year')
            year.text = str(value[:4])
            air_date = ET.SubElement(root,'aired')
            air_date.text = str(value)
        elif key == 'Network/Station':
            network = ET.SubElement(root, 'network')
            '''if '/' in value:
                network_station = value.split('/')
                affiliate = re.search(r'\s\d+$',value)
                if affiliate == True:
                    print(affiliate)
                    affiliate_text = affiliate.group(1)
                    channel_number = affiliate.group(2)
                    network.text = f"Network: {network_station[0]}, Affiliate: {affiliate.group(1)}, Channel: {affiliate.group(2)}"
            else:'''
            network.text = value
        elif key == 'Description':
            plot = ET.SubElement(root, 'plot')
            plot.text = value
            outline = ET.SubElement(root, 'outline')
            outline.text = value
        elif key == 'Tags':
            tag_list = value.split(',')
            for tag in tag_list:
                tag = tag.strip()
                tag_element = ET.SubElement(root, 'tag')
                tag_element.text = tag
        elif key == "Title":
            title = ET.SubElement(root, 'title')
            title.text = value
        elif key == "Filename":
            filename_key = ET.SubElement(root, 'original_filename')
            filename_key.text = value
        elif key == 'Tape ID':                
            tape_id = value
        elif key == 'Location':
            location = ET.SubElement(root, 'locationinfo')
            location.text = value
        elif key == 'Frame Range':
            in_frame = value[0]
            out_frame = value[1]
            
        elif key == 'Uploaded':
            for provider, details in value.items():
                for subkey, subvalue in details.items():
                    if subkey == 'url':
                        uploaded = ET.SubElement(root, 'trailer')
                        dateadded = ET.SubElement(root, 'dateadded')
                        if provider.lower() == 'youtube':
                            uploaded.text = f"plugin://plugin.video.youtube/?action=play_video&amp;videoid={subvalue.split('v=')[-1]}"
                        else:
                            uploaded.text = subvalue
                    elif subkey == 'datetime':
                        dateadded.text = subvalue

    clip_id = f"{tape_id}_{in_frame}-{out_frame}"
    xml_id = ET.SubElement(root,'id')
    xml_id.text = clip_id
    # Convert the ElementTree to a string
    #xml_string = ET.tostring(root, encoding='utf-8').decode('utf-8')
    return root

def nfo_from_json(json_path):
    print("[ACTION] Generating NFO files from JSON Data")
    json_directory = os.path.dirname(json_path)
    with open(json_path, 'r', encoding='utf-8') as file:
        json_array = json.load(file)
    for i, json_data in enumerate(json_array):
        xml_data = create_xml_from_json(json_data)
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', ".webm", ".m4v"]
        print(f"Processing {json_data['Filename']}")
        clip_path = os.path.join(json_directory,json_data['Filename'])
        try:
            clip = VideoFileClip(clip_path)
        except:
            continue
        #print(clip_path)
        # Get the attributes and methods of the VideoFileClip object
        attributes_and_methods = [attr for attr in dir(clip) if not callable(getattr(clip, attr)) and not attr.startswith("__")]

        fileinfo = ET.SubElement(xml_data,'fileinfo')
        streamdetails = ET.SubElement(fileinfo,'streamdetails')
        video_xml = ET.SubElement(streamdetails,'video')
        audio_xml = ET.SubElement(streamdetails,'audio')
        
        # Video details
        video_codec = ET.SubElement(video_xml,'codec')
        #video_codec.text = clip.fmt
        width = ET.SubElement(video_xml,'width')
        height = ET.SubElement(video_xml,'height')
        size_w, size_h = clip.size
        width.text = str(size_w)
        height.text = str(size_h)
        duration = ET.SubElement(video_xml,'durationinseconds')
        duration.text = str(clip.duration)
        frame_rate = clip.fps
        stereomode = ET.SubElement(video_xml,'stereomode')
        # Audio details
        audio_codec = ET.SubElement(audio_xml,'codec')
        #audio_codec.text = clip.audio.fmt
        channels = ET.SubElement(audio_xml,'channels')
        channels.text = str(clip.audio.nchannels)
        clip.close()

        video_codec.text, audio_codec.text = get_video_audio_codecs(clip_path)

        # Other Info
        source = ET.SubElement(xml_data,'source')
        source.text = "VHS"
        edition = ET.SubElement(xml_data,'edition')
        edition.text = "NONE"
        
        xml_declaration = f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n<!--created on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - VHSTools -->"

        # Serialize the XML tree to a string with pretty printing
        xml_str = ET.tostring(xml_data, encoding='utf-8', method='xml').decode('utf-8')
        # Use the pretty-printed XML string
        formatted_xml = minidom.parseString(xml_str).toprettyxml(indent='  ').replace('<?xml version="1.0" ?>', xml_declaration)
        xml_string = formatted_xml

        # Saving NFO File
        nfo_filename = os.path.splitext(json_data['Filename'])[0] + '.nfo'
        nfo_path = os.path.join(json_directory, nfo_filename)
        with open(nfo_path, 'w', encoding='utf-8') as nfo_file:
            nfo_file.write(xml_string)
            
def get_video_audio_codecs(file_path):
    try:
        probe = ffmpeg.probe(file_path, v='error')
        streams = probe['streams']
        
        video_codec = next((stream['codec_name'] for stream in streams if stream['codec_type'] == 'video'), None)
        audio_codec = next((stream['codec_name'] for stream in streams if stream['codec_type'] == 'audio'), None)

        return video_codec, audio_codec
    except ffmpeg.Error as e:
        print("Error:", e.stderr)
        return None