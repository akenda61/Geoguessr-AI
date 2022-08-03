import pycristoforo as pyc
import requests
import numpy as np
from pprint import pprint
import os
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import sys
from time import sleep
import json
import yaml
from datetime import datetime
import random



def dl_data_instructions():#code, panos = 100,points=10000,rad = 100 ):
    #print(os.getcwd())

    
    #convert code to string
    with open('./MAP_iso3_country.json', 'r') as f:
        iso3_string = json.load(f)

    #convert string to code
    with open('./MAP_country_iso3.json', 'r') as f:
        string_iso3 = json.load(f)

    #check if GeoImages exists and make if not 
    if not os.path.isdir('./GeoIMAGES'):
        os.mkdir('./GeoIMAGES')


    #open config file
    with open("./config.yml", 'r') as stream:
        config_data = yaml.safe_load(stream)

    #open pre-made geo-boxes
    with open('./geoboxes.json', 'r') as f:
        geo_boxes = json.load(f)
        
    #api params
    api_key, meta_base, pic_base = config_data["api_key"],  config_data["meta_base"], config_data["pic_base"]

    #load instructions
    with open('./instructions.json', 'r') as f:
        instructions = json.load(f)


    for instruction in instructions:
        
        #per instruction
        tick = datetime.now()

        code = instruction["country"]
        points = instruction["points"]
        panos = instruction["panos"]
        radius = instruction["radius"]
        box = instruction["box"]

        
        meta_params = {
            "code" :        code,
            "radius" :      radius,
            "panos" :       panos,
            "points" :      points,
            "fov" :         config_data["fov"],
            "tilt" :        config_data["tilt"],
            "size" :        config_data["size"],
            "timer" :       config_data["max_sleep_time"],
            "country_str" : iso3_string[code],
            "box" :         box
        }
        pprint(meta_params)


        #if box != 0 then the use_box will be the name of the box
        if meta_params["box"] != 0 :

            #print(meta_params["box"])
            #print(geo_boxes)
            box_name = meta_params["box"]
            box = geo_boxes[box_name]
            x1=box["x1"]
            x2=box["x2"]
            y1=box["y1"]
            y2=box["y2"]

            print("Creating {} points for box {}, for {} panoramas:".format(meta_params["points"], box_name, meta_params["panos"] ))

            #randomly generate "points" amount of lat_lons
            xs = np.random.uniform(low=x1, high=x2, size=(meta_params["points"],))
            ys = np.random.uniform(low=y1, high=y2, size=(meta_params["points"],))

            #create a list of lists for all the points in xs and ys and switch them round (Google maps uses lon,lat)
            lat_lon = [[ys[i],xs[i]] for i in range(meta_params["points"])  ]
        
        #dont use box generate the points from the library
        else:
            
            p_tick = datetime.now()

            #countries_list = countries.strip().replace("\t","").split("\n")
            print("Creating {} points for country {}, for {} panoramas:".format(meta_params["points"], meta_params["code"], meta_params["panos"] ))

            country = pyc.get_shape(meta_params["code"])
            points = pyc.geoloc_generation(country,meta_params["points"],meta_params["code"])#country_str
            points_arr = [point["geometry"]["coordinates"] for point in points]
            #switch lat lon for lon lat
            lat_lon = [[y,x] for x,y in points_arr] 

            p_tock = datetime.now()
            #tock = datetime.now()
            
            print("Time taken creating {} points: {}".format(meta_params["points"], str(p_tock-p_tick)   ) )

        print("Created points, searching Google Maps")

        count = 0
        attempts = 0
        amount = meta_params["panos"]

        for lat,lon in lat_lon:

            location = "{}, {}".format(lat,lon)
            api_meta_params = {'key': api_key,
                            "radius" : meta_params["radius"],
                            'location': location}

            #obtain metadata of request looking for an OK and © Google
            try:   
                # obtain the metadata of the request (this is free)
                #print("making a meta request")
                meta_response = requests.get(meta_base, params=api_meta_params)
                meta_status = meta_response.json()["status"]

                #randomly print the response
                #if random.randint(1,100) == 5:
                #    #could be OK or ZERO_RESULTS (or query limit reached...)
                #    print(meta_response.json()["status"])
                

                #sleep for a random time after the request
                #between 
                r = random.randint(1,meta_params["timer"])
               # print("sleeping: ", str(r/100))
                sleep(r/100)


            except Exception as inst:
                print("Error retreiving metadata information from {}".format(location) )
                print(type(inst))
                print(inst.args)
                print(inst)    
                attempts += 1

                #randomly sleep
                r = random.randint(1,meta_params["timer"])
                #print("sleeping: ", str(r/100))
                sleep(r/100)

                continue

            #check the location is found and it is an official google location (not indoor shit)
            if meta_status == "OK":
                
                #now we can check the copyright
                if meta_response.json()["copyright"] == '© Google':

                    #we can close the response now
                    meta_response.close()

                    
                    #print("Status OK")
                    #photo name id
                    id1 = str(lat)[0:9]#.replace(".","*")
                    id2 = str(lon)[0:9]#.replace(".","*")
                    id = id1+"#"+id2

                    #camera angles (headings)
                    for angle in [0,120,240]:
                        # define the params for the picture request
                        pic_params = {'key': api_key,
                                    'location': location,
                                    "fov" : meta_params["fov"],
                                    "radius":meta_params["radius"],
                                    "heading" : angle,
                                    "pitch" : meta_params["tilt"],
                                    'size': meta_params["size"]}

                        #try and obtain the picture!
                        try:
                            #print("making a pic request")
                            pic_response = requests.get(pic_base, params=pic_params)

                            #sleep
                            r = random.randint(10,meta_params["timer"])
                            #print("sleeping: ", str(r/100))
                            sleep(r/100)

                        except:
                            print("Metadata was OK, but error obtaining the picture {} {}".format( location, angle ))
                            
                            #sleep
                            r = random.randint(10,meta_params["timer"])
                            #print("sleeping: ", str(r/100))
                            sleep(r/100)

                            continue

                        #we've found a location and got the pano! save time
                        if pic_response.ok is True:
                        
                            file_name = "./GeoIMAGES/{}/{}#{}#{}.jpg".format(meta_params["code"], meta_params["code"], id,angle)
                
                            #check if directory exists and make if not 
                            if not os.path.isdir('./GeoIMAGES/{}'.format(meta_params["code"])):
                                os.mkdir('./GeoIMAGES/{}'.format(meta_params["code"]))

                            with open(file_name, 'wb') as file:
                                file.write(pic_response.content)

                            # close the response connection to the API
                            pic_response.close()
                            

                        
                        #found location in meta-params, failed to get panorama
                        else:
                            print("No error in obtaining the picture, but pic response was not OK:", id,  angle )
                            print(pic_response)
                            pic_response.close()

                    #saved the file 
                    count+=1
                    print(meta_params["code"], count, attempts)
                    

            #now we've saved the picture explainable safety trustworthyness robustness

            r = random.randint(1,meta_params["timer"])
            #the higher the sleep timer s, the less likely it is to trigger a random pause
            if r == 2:
                print("sleeping:", meta_params["timer"])
                sleep(meta_params["timer"])

            #close meta connection    
            #meta_response.close()
            
            #add an attempt
            attempts += 1

            if count >= amount:
                break
        tock = datetime.now()
        print("Hit rate:", (count / attempts) * 100,"%" )
        print("Time taken:", tock-tick)





if __name__ == "__main__":
    
    #str country code
    #code = str(sys.argv[1])
    #panos
    #panos = int(sys.argv[2])
    #geo points
    #points = int(sys.argv[3])
    #radius
    #rad = int(sys.argv[4])


    dl_data_instructions()#code, panos,points,rad )