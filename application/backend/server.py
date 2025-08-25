#imports
from typing import Annotated
import json, http.server, os, csv, sys
import numpy as np
from fastapi import  FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import random
import selfSort


#establish backend server
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a user config file for a new user - picks one row from the Latin square and permutes the columns
def createUserConfig(uid):
    # First get config row for the user
    userConfigData = []
    with open("configLatinSquare.csv", "r") as configFile:
        reader = csv.reader(configFile, delimiter=';')
        readRows = 0
        for row in reader:
            # Get current user config
            if readRows == uid:
                for item in row:
                    splitItem = item.split(",")
                    userConfigData.append({"ord": splitItem[1], "size": int(splitItem[0])})
                break
            readRows += 1

    # Get number of datasets
    datasetCount = len([folder for folder in os.listdir("./Data/") if os.path.isdir(os.path.join("./Data/", folder))])
 
    # Get all attention check dataset indices (each line in file)
    attentionCheckIndices = []
    if os.path.isfile("./Data/attentionCheckIndices.txt"):
        with open("./Data/attentionCheckIndices.txt", "r") as attentionCheckFile:
            for line in attentionCheckFile:
                datasetIndex = int(line.strip())
                if not datasetIndex in attentionCheckIndices:
                    attentionCheckIndices.append(datasetIndex)
     
    # Get number of attention checks
    numOfAttentionChecks = len(attentionCheckIndices)
    realDatasetCount = datasetCount - numOfAttentionChecks  # Actual full datasets
 
    # Then add (real) dataset to each config - skipping the attention check indices
    realDatasetIndex = 0
    for i in range(datasetCount):
        if i not in attentionCheckIndices:
            if realDatasetIndex < len(userConfigData):
                userConfigData[realDatasetIndex]["dataset"] = i
                realDatasetIndex += 1
     
    # Taky only the real dataset count elements from the user config
    userConfigData = userConfigData[:realDatasetCount]

    # Now get a random permutation of the user config (real datasets only)
    random.shuffle(userConfigData)

    # Insert back attention checks (ord = sp and size = 4) evenly into the user config
    for i in range(len(attentionCheckIndices)):
        # e.g. for 3 attention checks, insert at 1/4, 2/4, 3/4
        userConfigData.insert(int((i+1) * datasetCount / (numOfAttentionChecks + 1)), {"dataset": attentionCheckIndices[i], "ord": "sp", "size": 4})


    # Finally store the new user config in user's folder as a csv file (each row contains three items)
    with open(f"CollectedData/{uid:04}/userConfig.csv", "w") as configFile:
        writer = csv.writer(configFile, delimiter=';')
        for configRow in userConfigData:
            writer.writerow([configRow["dataset"], configRow["ord"], configRow["size"]])
    print(f"User config created for user {uid}.")
    
#helper function to get the last user id
def getHighestUserID():
    folder_names = [name for name in os.listdir("CollectedData") if os.path.isdir(os.path.join("CollectedData", name))]
    numeric_folders = [int(name) for name in folder_names if name.isdigit()]
    print(numeric_folders)
    return max(numeric_folders, default=-1)

#helper function to get next user
def getMissingUserID():
    folder_names = [name for name in os.listdir("CollectedData") if os.path.isdir(os.path.join("CollectedData", name))]
    numeric_folders = [int(name) for name in folder_names if name.isdigit()]
    for j in range(len(numeric_folders)):
        if (j) not in numeric_folders:
            return (j-1)
    return getHighestUserID()

#creates a novel user
def createNewUser(userId):
    # get last user ID
    maxUserID = getMissingUserID()

    # get new user ID
    newUid = maxUserID + 1

    #initialize logs
    logs = {}
    # store new user to .json
    logs[str(newUid)] = {"lastCompleted" : -2, "userId" : userId, "reloads" : {}, "totalIncorrect" : 0}  # -2 to indicate that the user is new
    logsStr = json.dumps(logs, indent=4)
    
    os.makedirs(f"CollectedData/{newUid:04}", exist_ok=True)
    with open(f"CollectedData/{newUid:04}/userData.json", "w") as JSONfile:
        JSONfile.write(logsStr)

    # Also create empty scrollPositions.txt and submissions.txt
    with open(f"CollectedData/{newUid:04}/scrollPositions.txt", "w") as scrollFile:
        pass
    with open(f"CollectedData/{newUid:04}/submissions.txt", "w") as submissionFile:
        pass

    # Also add mapping PID to UID to a csv file (create if it does not exists)
    with open("CollectedData/pid_uid_mapping.csv", "a") as mappingFile:
        writer = csv.writer(mappingFile, delimiter=';')
        writer.writerow([userId, newUid])

        # Also create a user config file
    createUserConfig(newUid)
    return newUid



#handle api call to create a new user
@app.post("/api/newUser")
async def newUser(req: Request):
    params = await req.json()
    userId = str(params['userId'])
    newUid = createNewUser(userId)
    response = {'new_id': newUid, 'numOfSets': len([folder for folder in os.listdir("./Data/") if os.path.isdir(os.path.join("./Data/", folder))])}
    response = json.dumps(response).encode('utf-8')
    return response

#handle api call to load images based on the user/iteration
@app.post("/api/getImages")
async def getImages(req: Request):
    params = await req.json()
    #get user id
    uid = str(params['uid']) if 'uid' in params else None
    #get current iteration
    iteration = str(params['iteration']) if 'iteration' in params else None
    if uid == None or iteration == None:
        return

    #load the image sets from the data folder
    imageSets = [folder for folder in os.listdir("./Data/") if os.path.isdir(os.path.join("./Data/", folder))]
    imageSets.sort(key=int)

    # load currently saved data
    with open(f"CollectedData/{int(uid):04}/userData.json", "r") as JSONfile:
        logs = json.load(JSONfile)
        userLogs = logs.get(uid,{})
        dataSets = userLogs.get("dataSets",{})

    # load board config from user config file
    configData = []
    with open(f"CollectedData/{int(uid):04}/userConfig.csv", "r") as configFile:
        reader = csv.reader(configFile, delimiter=';')
        for row in reader:
            configData.append({"dataset": int(row[0]), "ord": row[1], "size": int(row[2])})

    # Get size and sorting method for the current iteration
    imagesOnRow = configData[int(iteration) % len(configData)]['size']
    sortingMethod = configData[int(iteration) % len(configData)]['ord']

    #load feature filenames for sorting if necessary
    if sortingMethod == "ss":
        featuresFileName = "CLIPFeatures.csv"
    elif sortingMethod == "lab":
        featuresFileName = "LABFeatures.csv"
    images = []
    clipFeatures = {}
    if(len(dataSets) < len(imageSets)):
        chosenFolder = imageSets[configData[int(iteration) % len(configData)]['dataset'] % len(imageSets)]

        # Get list of only .jpg files in the folder
        images = [file_name for file_name in os.listdir("./Data/" + chosenFolder + "/") if file_name.endswith('.jpg')]
 

        # Sort the images by name (to ensure consistent order across different operating systems)
        images.sort()
                
        #sort images based on self sorting
        if sortingMethod == "ss" or sortingMethod == "lab":
            with open("./Data/" + chosenFolder + "/" + featuresFileName, "r") as featuresFile:
                reader = csv.reader(featuresFile, delimiter=';')
                rowID = 0
                for row in reader:
                    clipFeatures[images[rowID]] = row
                    rowID += 1
    else: # end of test - out of dataSets
        chosenFolder = "END"

    #update user logs for next iteration
    lastCompletedIter = userLogs.get("lastCompleted", -2)
    userLogs["lastCompleted"] = lastCompletedIter + 1
    reloads = userLogs.get("reloads",{})
    reloads[lastCompletedIter + 2] = 0
    userLogs["reloads"] = reloads
    logs[uid] = userLogs
    logsStr = json.dumps(logs, indent=4)
    
    #write json file to logs
    with open(f"CollectedData/{int(uid):04}/userData.json", "w") as JSONfile:
        JSONfile.write(logsStr)

    #load target image from candidate set
    targetImage = ""
    sorted_images = np.array(images)
    if (chosenFolder != "END"):
        # same image for each dataset
        with open("./Data/" + chosenFolder + "/chosenTarget.txt", "r") as targetFile:
            targetImage = targetFile.readline()  

        if sortingMethod == "ss" or sortingMethod == "lab":
            # Convert the map's arrays from strings to floats
            float_map = {k: np.array(list(map(float, v))) for k, v in clipFeatures.items()}

            # Collect all float arrays into a single NumPy array
            X = np.array(list(float_map.values()))
            # We need a 2D array
            X = X.reshape(len(images), -1).astype(np.float32)


            print(f"Sorting images using {sortingMethod} method.")
            _, sorted_images = selfSort.sort_with_flas(X.copy(), images, nc=49, n_images_per_site=imagesOnRow, radius_factor=0.7, wrap=False)

    # send dataset and list of contents back to JS
    response = {'images': images, 'folder' : chosenFolder, 'boardSize' : imagesOnRow, 'sortingMethod' : sortingMethod, 'target' : targetImage, 'ss_images' : sorted_images.tolist()}    
    response = json.dumps(response).encode('utf-8')
    return response



#handle call to store scroll positions
@app.post("/api/scrollPositions")
async def scrollPositions(req: Request):
    request = await req.json()
    uid = str(request["uid"])
    iteration = str(request["iteration"])
    logJSON = json.loads(request["log"])
    scrollData = logJSON["multipleScrollData"]
    toLogText = ""
    for scrollLog in scrollData:
        toLogText += str(uid)+";"+str(iteration)+";"+str(scrollLog["timestamp"])+";"+str(scrollLog["scrollPos"])+";"+str(scrollLog["totalScroll"])+";"+str(scrollLog["windowW"])+";"+str(scrollLog["windowH"])+";"+str(scrollLog["navbarH"])+";"+str(scrollLog["firstRowStart"])+";"+str(scrollLog["secondRowStart"])+";"+str(scrollLog["imageHeight"])+";"+str(scrollLog["missedTarget"])+";"+str(scrollLog["afterLoad"])+"\n"
    with open(f"CollectedData/{int(uid):04}/scrollPositions.txt", 'a') as csvFile:
        csvFile.write(toLogText)
    
    response = {}
    response = json.dumps(response).encode('utf-8')
    return response

#handle call to store submissions
@app.post("/api/submissions")
async def submissions(req: Request):
    request = await req.json()
    uid = str(request["uid"])
    iteration = request["iteration"]
    logJSON = request
    toLogText = str(uid)+";"+str(iteration)+";"+str(logJSON["timestamp"])+";"+str(logJSON["scrollPos"])+";"+str(logJSON["totalScroll"])+";"+str(logJSON["navbarH"])+";"+str(logJSON["windowH"])+";"+str(logJSON["firstRowStart"])+";"+str(logJSON["secondRowStart"])+";"+str(logJSON["imageHeight"])+";"+str(logJSON["correct"])+";"+str(logJSON["image"])+"\n"

    # write csv data to disk
    with open(f"CollectedData/{int(uid):04}/submissions.txt", 'a') as csvFile:
        csvFile.write(toLogText)
    
        # If the submission was incorrect (0), increment the total incorrect counter
        if logJSON["correct"] == 0:
            # load currently saved data
            with open(f"CollectedData/{int(uid):04}/userData.json", "r") as JSONfile:
                logs = json.load(JSONfile)
                userLogs = logs.get(uid,{})
 
            userLogs["totalIncorrect"] = userLogs.get("totalIncorrect", 0) + 1
 
            # save new data in JSON file
            logs[uid] = userLogs
            logsStr = json.dumps(logs, indent=4)
                 
            with open(f"CollectedData/{int(uid):04}/userData.json", "w") as JSONfile:
                JSONfile.write(logsStr)

    response = {}
    response = json.dumps(response).encode('utf-8')
    return response

#load an old user, e.g. because of reloads
@app.post("/api/oldUser")
async def oldUser(req: Request):
    request = await req.json()
    # Get user id
    userId = request["userId"]
    loadFailed = 0

                # Get user ID from mapping file
    oldUser = "-1"

    # Check if file exists, if not create it
    if not os.path.exists("CollectedData/pid_uid_mapping.csv"):
        with open("CollectedData/pid_uid_mapping.csv", "w") as f:
            pass  # Creates an empty file
    try:
        with open("CollectedData/pid_uid_mapping.csv", "r") as mappingFile:
            reader = csv.reader(mappingFile, delimiter=';')
            for row in reader:
                if row[0] == userId:
                    oldUser = row[1]
                    break
    except FileNotFoundError:
        pass

    if oldUser == "-1":
        loadFailed = 1
        userLogs = {}


    try:
        with open(f"CollectedData/{int(oldUser):04}/userData.json", "r") as JSONfile:
            logs = json.load(JSONfile)
            userLogs = logs[str(oldUser)]
    except Exception as e:  # file empty
        loadFailed = 1
        userLogs = {}
            
    lastCompletedIter = userLogs.get("lastCompleted", -1)
    userLogs["lastCompleted"] = lastCompletedIter
    currIter = str(lastCompletedIter + 1)

    reloads = userLogs.get("reloads",{})
    reloads[currIter] = reloads.get(str(currIter), 0) + 1
    userLogs["reloads"] = reloads

    if (loadFailed == 0):
        # update user data in json
        logs[str(oldUser)] = userLogs
        logsStr = json.dumps(logs, indent=4)
                
        with open(f"CollectedData/{int(oldUser):04}/userData.json", "w") as JSONfile:
            JSONfile.write(logsStr)

    response = {'loadFailed': loadFailed, 'userID' : oldUser, 'currIter' : int(currIter),'currImages' : [item['image'] for item in userLogs.get("imagePos", {}).get(currIter, [])], 'currTarget' : userLogs.get("targets", {}).get(currIter, "END"), 'currBoardSize' : userLogs.get("imagesPerRow", {}).get(currIter, 4), 'currDataFolder' : userLogs.get("dataSets", {}).get(currIter, "END"), 'currOrdering' : userLogs.get("orderings", {}).get(currIter, "missing"), 'numOfSets': len([folder for folder in os.listdir("./Data/") if os.path.isdir(os.path.join("./Data/", folder))]), 'totalIncorrect' : userLogs.get("totalIncorrect", 0)}
    response = json.dumps(response).encode('utf-8')
    return response


#handler to store the current image config (placement of images)
@app.post("/api/imageConfig")
async def imageConfig(req: Request):
    jsonPayload = await req.json()    
    positions = json.loads(jsonPayload["positions"])
    uid = str(jsonPayload["uid"])
    iteration = str(jsonPayload["iteration"])
    target = jsonPayload["target"]
    dataSet = jsonPayload["dataSet"]
    ordering = jsonPayload["ordering"]
    perRow = jsonPayload["perRow"]
            
    # load currently saved data
    with open(f"CollectedData/{int(uid):04}/userData.json", "r") as JSONfile:    
        logs = json.load(JSONfile)
        userLogs = logs.get(uid,{})

    # write new data
    posData = userLogs.get("imagePos",{})
    posData[iteration] = positions
    userLogs["imagePos"] = posData

    targetsData = userLogs.get("targets",{})
    targetsData[iteration] = target
    userLogs["targets"] = targetsData

    dataSets = userLogs.get("dataSets",{})
    dataSets[iteration] = dataSet
    userLogs["dataSets"] = dataSets

    orderings = userLogs.get("orderings",{})
    orderings[iteration] = ordering
    userLogs["orderings"] = orderings

    imagesPerRow = userLogs.get("imagesPerRow",{})
    imagesPerRow[iteration] = perRow
    userLogs["imagesPerRow"] = imagesPerRow
            
    # save new data in JSON file
    logs[uid] = userLogs
    logsStr = json.dumps(logs, indent=4)
    with open(f"CollectedData/{int(uid):04}/userData.json", "w") as JSONfile:
       
        JSONfile.write(logsStr)

    response = {}
    response = json.dumps(response).encode('utf-8')
    return response
    

