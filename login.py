from flask import Flask, render_template, request, redirect, url_for, session
import http.client
import math
import time
import json
import urllib.request
import urllib.parse
import re

app = Flask(__name__)
app.secret_key = 'dummy_secret_key'

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        #username = request.form['username']
        #password = request.form['password']
        accessToken = request.form['password']
        session['dummy'] = {'token': accessToken, 'sizeFrom': '0', 'sizeTo': '0', 'count': '0', 'keywords': ''}
        #authResponse = authenticate(username, password)
        authResponse = authenticate(accessToken)
        if authResponse == 'success':
            return redirect(url_for('search'))
        else:
            error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)

@app.route('/search', methods=['GET', 'POST'])
def search():
    error = None
    if request.method == 'POST':
        start_time = time.time()
        language = request.form['language']
        searchBy = request.form['searchBy']
        keywords = request.form['keywords']
        fileSizeFrom = request.form['fileSizeFrom']
        fileSizeTo = request.form['fileSizeTo']
        fileCount = request.form['fileCount']
        if fileSizeFrom == None or fileSizeFrom == "":
            fileSizeFrom = 0
        if fileSizeTo == None or fileSizeTo == "":
            fileSizeTo = 384
        if fileCount == None or fileCount == "":
            fileCount = 1000
        if int(fileSizeTo) < int(fileSizeFrom):
            error = 'Please specify the file size range values correctly.'
        elif keywords == None or keywords == "":
            error = 'Please specify at least one keyword.'
        else:
            mySession = session.get('dummy', {})
            mySession['sizeFrom'] = fileSizeFrom
            mySession['sizeTo'] = fileSizeTo
            mySession['keywords'] = keywords
            downloadedFileCount = 0
            if downloadedFileCount < int(fileCount) and searchBy == "s":
                structuralKeywords = getKeywordFromGPTAPI(language, keywords)
                for keyword in structuralKeywords:
                    downloadedFileCount += download(language, keyword, fileSizeFrom, fileSizeTo, str(int(fileCount) - downloadedFileCount), mySession['token'])
                    if downloadedFileCount >= int(fileCount):
                        break
            if downloadedFileCount < int(fileCount):
                downloadedFileCount += download(language, keywords, fileSizeFrom, fileSizeTo, str(int(fileCount) - downloadedFileCount), mySession['token'])
            timeInSec = time.time() - start_time
            mySession['count'] = str(downloadedFileCount)
            mySession['timeInSec'] = str(timeInSec)
            session['dummy'] = mySession
            return redirect(url_for('dashboard'))
        return render_template('search.html', error=error)
    return render_template('search.html', error=error)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    mySession = session.get('dummy', {})
    fileCount = mySession['count']
    time = mySession['timeInSec']
    return render_template('dashboard.html', fileCount=fileCount, time=time)

#def authenticate(username, accessToken):
def authenticate(accessToken):
    conn = http.client.HTTPSConnection("api.github.com")
    payload = ''
    authQuery = '/search/code?q=.sql+in:path+size:1..1'
    headers = {
      'User-Agent': 'dummyUser',
      'Authorization': 'Bearer ' + accessToken
    }
    conn.request("GET", authQuery, payload, headers)
    res = conn.getresponse()
    data = res.read()
    if res.status != 200:
        return 'Authentication failed. Please try again'
    else:
        return 'success'

def download(language, keywords, fileSizeFrom, fileSizeTo, fileCount, accessToken):
    keywords = keywords.split(",")
    keywordsStr = ""
    for item in keywords:
        keyword = item.strip()
        keywordsStr += "\"" + keyword + "\" "
    keywordsStr = urllib.parse.quote(keywordsStr)
    minSrcFileSize = int(fileSizeFrom)*1024 # in bytes
    maxSrcFileSize = int(fileSizeTo)*1024
    srcFileCount = int(fileCount)
    safetyFactor = 2 # for avoiding downloading less files than specified because of overlapping results
    maxItemsFromAPI = 1000 #as per API documentation
    maxItemsPerPage = 100 # as per API documentation
    maxPageNoFromAPI = 10
    noOfBuckets = math.ceil(srcFileCount*safetyFactor/maxItemsFromAPI)
    noOfBuckets = min(maxSrcFileSize - minSrcFileSize + 1, noOfBuckets)
    fileBucketSize = math.floor((maxSrcFileSize - minSrcFileSize + 1)/noOfBuckets)
    
    firstPage = 1
    lastPage = math.ceil(srcFileCount*safetyFactor/(noOfBuckets*maxItemsPerPage))
    lastPage = min(lastPage, maxPageNoFromAPI)

    stage1OutputPath = './1_SearchQueries.txt'
    stage2OutputDir = './2_APIResponses/'
    #stage2OutputDir2 = './2_APIResponses2/'
    stage3OutputPath = './3_SrcCodeUrls.txt'
    stage4OutputDir = './4_SrcCodeFiles/'
    stage5OutputPath = './5_Stats.txt'

    outPath = stage1OutputPath
    searchQueryFile = open(outPath, 'w')

    for p in range (firstPage, lastPage+1):
        for s in range (minSrcFileSize, maxSrcFileSize, fileBucketSize):
            s_l = s
            s_u = s + fileBucketSize - 1
            searchQuery = "/search/code?q="+keywordsStr+"+in:file+language:"+language+"+size:" + str(s_l) + ".." + str(s_u)
            searchQuery = searchQuery + "&per_page=" + str(maxItemsPerPage) + "&page=" + str(p)
            searchQueryFile.write(searchQuery + "\n")
    searchQueryFile.close()

    # For saving the json responses
    inPath = stage1OutputPath
    outDirPath = stage2OutputDir

    # For identifying the unique download urls
    inDirPath = stage2OutputDir
    outPath = stage3OutputPath

    # For processing json response to construct download urls
    rawGithubPrefix = 'https://raw.githubusercontent.com/'
    githubPrefix = 'https://github.com/'
    blobStr = 'blob/'

    srcFileCounter = 1
    srcUrlFile = open(outPath, 'w')
    uniqueSrcUrls = set()

    # For downloading files to this location
    downloadDir = stage4OutputDir
    notRetrieved = set()

    # the following are two variables for determining the response file name
    b = 0
    p = firstPage
    searchQueryFile = open(inPath, 'r')
    #searchQueryList = searchQueryFile.readlines()[300:]
    #srcFileIndex = 1
    while True:
        searchQuery = searchQueryFile.readline().strip()
        #searchQuery = searchQueryList[srcFileIndex].strip()

        if searchQuery=='':
            break
        
        conn = http.client.HTTPSConnection("api.github.com")
        payload = ''
        headers = {
          'User-Agent': 'dummyUser',
          'Authorization': 'Bearer ' + accessToken
        }
        conn.request("GET", searchQuery, payload, headers)
        res = conn.getresponse()
        data = res.read()
        while res.status != 200:
            time.sleep(11)
            conn = http.client.HTTPSConnection("api.github.com")
            payload = ''
            headers = {
            'User-Agent': 'dummyUser',
            'Authorization': 'Bearer ' + accessToken
            }
            conn.request("GET", searchQuery, payload, headers)
            res = conn.getresponse()
            data = res.read()
        text = data.decode("utf-8")

        b += 1
        if b > noOfBuckets:
            b = 1
            p+= 1
        responseFilePath = outDirPath+"B"+str(b)+"_P"+str(p)+".json"
        
        responseFile = open(responseFilePath, "w")
        responseFile.write(text)
        responseFile.close()

        repoJsonFile = open(responseFilePath)
        repoData = json.load(repoJsonFile)
        repoList = repoData['items']
        for repo in repoList:
            if  repo['repository']['private']:
                print ('ERROR - Access Denied\nPrivate Repository: ' + repo['html_url'])
            else:
                raw_url = repo['html_url'].replace(blobStr, '').replace(githubPrefix, rawGithubPrefix)
                if raw_url not in uniqueSrcUrls:
                    uniqueSrcUrls.add(raw_url)
                    ext = raw_url.rsplit(".", 1)
                    if len(ext) > 1:
                        ext = "." + ext[1]
                    else:
                        ext = ""
                    srcUrlFile.write(raw_url + '\n')
                    srcUrlFile.close()
                    srcUrlFile = open(outPath, 'a')
                    try:
                        urllib.request.urlretrieve(raw_url, downloadDir + str(srcFileCounter) + ext)
                    except Exception:
                        notRetrieved.add(srcFileCounter)
                    srcFileCounter += 1

                if srcFileCounter > srcFileCount:
                    break
            if srcFileCounter > srcFileCount:
                break
        if srcFileCounter > srcFileCount:
            break

        #if srcFileCounter%100 == 0:
            #print(str(srcFileCounter) + " files downloaded")
        
    srcUrlFile.close()
    print(str(srcFileCounter - len(notRetrieved) - 1)  + " files downloaded")
    print('Not retrieved: ' + str(len(notRetrieved)))
    errorFile = open('4_error.txt', 'w')
    for item in notRetrieved:
        errorFile.write(str(item))
    errorFile.close()
    return srcFileCounter-1

def getKeywordFromGPTAPI(language, keywords):
    conn = http.client.HTTPSConnection("api.openai.com")
    queryStr = language + " " + keywords + "  keywords or syntax or operator. Answer only."
    max_tokens = 5
    auth_token_file = open('./openai_auth_token', 'r')
    auth_token = auth_token_file.readline().strip()
    payload = json.dumps({
      "model": "gpt-3.5-turbo",
      "messages": [
        {
          "role": "user",
          "content": queryStr
        }
      ],
      "max_tokens": max_tokens
    })
    
    headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + auth_token
    }
    conn.request("POST", "/v1/chat/completions", payload, headers)
    res = conn.getresponse()
    data = res.read()
    text = data.decode("utf-8")
    jsonResponse = json.loads(text)
    structuralKeywords = str(jsonResponse['choices'][0]['message']['content'])
    #print(structuralKeywords)
    structuralKeywords = re.sub(r'\(.*\)', '', structuralKeywords)
    #print(structuralKeywords)
    structuralKeywords = structuralKeywords.strip()
    structuralKeywords = structuralKeywords.split()
    #print(structuralKeywords)
    processedKeywords = []
    for items in structuralKeywords:
        items = items.split(",")
        #print(items)
        for item in items:
            item = item.strip()
            item = item.strip('.')
            item = item.strip(')')
            item = item.strip('(')
            if "\"" in item:
                item = item.replace("\"", "")
            if "'" in item:
                item = item.replace("'", "")
            if item.endswith("\n"):
                item = item.rstrip("\n")
            if len(item) > 0:
                processedKeywords.append(item)
    print(processedKeywords)
    return processedKeywords

if __name__ == '__main__':
    app.run(debug=True)