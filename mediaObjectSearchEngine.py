"""
mediaObjectSearchEngine.py
===============================================================================
Stephen Meyerhofer
Modified by - Nate Robinson
===============================================================================
NOTE:
  Lab 1 - Text Pre-Processing: The first step for an IR system is to to read in
    the text and decide what will be the processing unit to be worked with. For
    your first assignment, you will write a program that removes HTML tags and
    then will tokenize a web documents. We will experiment with different
    tokenization and token normalization techniques. You will see how these
    different techniques affect the dictionary size.
  Lab 2 - Web Crawling: You will be assigned a search engine (Google) and given
    a list of M=25 popular items from three domain (Books, Music Artist,
    Movies). For each item, you will be asked to download and tokenize the top
    n=10 web pages.
  Lab 3 - Indexing & Boolean Retrieval: Using the tokenized web documents, you
    will create a positional index from the corpus of MxN (250) documents. You
    will then created a text-based interface where a user can enter text-based
    boolean queries (AND, OR, PHRASAL, NEAR) to find relevant documents. In
    addition, you will also return the most relevant media objects (e.g.,
    movies or books or artists) by counting the number of relevant web pages
    that are associated with with each of the M items.
  Lab 4 - Ranked Retrieval: Similar to the previous lab, you will implement a
    ranked retrieval system that can be used to find relevant web pages and
    media objects.
  Lab 5 - Evaluation: Once we have a fully-implemented system, we quantify how
    well the system works using a number of standard evaluation metrics.

2/20/15-SM-Comments for submission to Doug and class.
2/17/15-SM-Code to build positional index. UI for lab 3 boolean retrieval
  queries.
2/10/15-SM-Modularized lab 2 and commented.
2/9/15-SM-Added metaSearch, build and delete directory functions, and
  executeQuery function. Updated main to complete lab 2.
2/4/15-SM-New.

Configuration Note:
If you want to use the Stanford tokenizer in the NLTK library, you need
to make sure this file is on their machine:

"/usr/share/nltk_data/stanford-postagger.jar” (In Lab3 folder on repo)

Otherwise, they will either have to change configuration.json to use a different tokenizer, or
change line 50 in naturalLanguageProcessing/tokenize.py for the path to this file.




"""

# TODO: Python documentation - DocStrings
# TODO: Python unit testing
# TODO: Clean Architecture
# TODO: Add comments to def's

# Built in imports.
import os
import shutil
import re
import time
import math
import operator
import random

# File imports.

from naturalLanguageProcessing          import stem as stemlib
from naturalLanguageProcessing.tokenize import tokenize
from random import shuffle
import spider
import configurationLoader
import metaSearch
from query import Query
from webDb import WebDb


db     = None
config = None
args   = None
pIndex = None
docWeight = None
queryWeight = None

def buildDirectoryStructure ( ):
    """
    Sets up data directory with the following sub-directories:
      clean
      header
      item
      raw
    """

    if not os.path.exists( 'data' ):
        os.makedirs( 'data' )
    if not os.path.exists( 'data/clean' ):
        os.makedirs( 'data/clean' )
    if not os.path.exists( 'data/header' ):
        os.makedirs( 'data/header' )
    if not os.path.exists( 'data/item' ):
        os.makedirs( 'data/item' )
    if not os.path.exists( 'data/raw' ):
        os.makedirs( 'data/raw' )


def deleteDirectoryStructure ( deleteWebPages=False ):
    """
    Delete tokenized and nomralized files in clean directory.
      If deleteWebPages is True, then delete files in header and raw
      directories, as well as the database cache and cookie file.
    """
    if ( deleteWebPages ):
        if os.path.exists( 'data/header' ):
            shutil.rmtree( 'data/header' )
        if os.path.exists( 'data/raw' ):
            shutil.rmtree( 'data/raw' )
        if os.path.isfile ( 'data/cache.db' ):
            os.remove( 'data/cache.db' )
        if os.path.isfile ( 'data/cookies.txt' ):
            os.remove( 'data/cookies.txt' )

    if os.path.exists( 'data/clean' ):
        shutil.rmtree( 'data/clean' )


def makeFileName ( ipInt ):
    """
    Based on input integer, append leading 0's to make a fileName
    6 numbers long.
    """

    string = str( ipInt )
    while ( len(string) < 6 ):
        string = "0" + string

    return string


def mediaItems ( ipDir ):
    """
    Generator function to return query string, media item name,
      and media type from files in input directory.
    """

    for mediaFile in os.listdir( ipDir ):
        firstLine = True
        itemType  = mediaFile.strip( '.txt' )
        query     = ""
        currentFile = open( ipDir+ '/' + mediaFile)
        for item in currentFile:
            itemName = item.strip()

            if ( firstLine ):
                query     = itemName
                firstLine = False
                continue
            else:
                yield query.replace( "(0)", itemName ), itemName, itemType


def writeToFile ( fileName, data, isList=False ):
    """
    Writes input data to fileName file. Able to handle list data,
    where each entry is written on a new line.
    """

    with open( fileName, 'w' ) as f:
        if ( isList ):
            for entry in data:
                f.write( entry + '\n' )
        else:
            f.write( data )


def storePageAndHeader ( url, webPage, headerInfo, itemName, itemType ):
    """
    Adds reford for url, item, and urlToItem tables in database.
    Writes webPage, header, and tokens to files.
    """

    title, tokens = spider.parse( webPage, args.tokenizer )
    lowerTokens   = spider.lower( tokens )
    stemTokens    = spider.stem( lowerTokens, args.stemmer )

    reStr  = "content-type:(?P<ct>(.*))"
    result = re.search( reStr, headerInfo, re.IGNORECASE )

    if not title:
        title = ""

    urlId  = db.insertCachedUrl( url, result.group( "ct" ), title )
    itemId = db.insertItem( itemName, itemType )
    u2iId  = db.insertUrlToItem( urlId, itemId )

    fileNum = makeFileName( urlId )
    writeToFile( "data/raw/"    + fileNum + ".html", webPage )
    writeToFile( "data/header/" + fileNum + ".txt",  headerInfo )
    writeToFile( "data/clean/"  + fileNum + ".txt",  stemTokens, True )

    print( urlId )


def restoreClean ( ):
    """
    Opens every file in data/raw directory, parsing, lowercasing,
    and stemming. Stores results in data/clean directory.
    """

    for htmlFileName in os.listdir( 'data/raw' ):
        with open( 'data/raw/' + htmlFileName ) as htmlFile:
            webPage = htmlFile.read( )

            title, tokens = spider.parse( webPage, args.tokenizer )
            lowerTokens   = spider.lower( tokens )
            stemTokens    = spider.stem( lowerTokens, args.stemmer )

            cleanFileName = htmlFileName.strip( '.html' )
            writeToFile( "data/clean/"  + cleanFileName + ".txt",  stemTokens, True )

            print( int(cleanFileName) )


def downloadFreshDocuments ( ):
    """
    Based on the media items in data/item directory, download 10 webpages
    with a query from the first line in each item file. Keep querying until
    10 pages have been successfullly download. Sleep for 60 seconds before
    requesting url results from the metaSearch engine. This throttling was
    successful with Google's ajax api on 2/10/15.

    Once pages are downloaded, parse, stem, and store them with the
    storePageAndHeader function.
    """

    for query, itemName, itemType in mediaItems( 'data/item' ):
        count = 10 - len(db.lookupUrlsForItem( itemName, itemType ))
        start = 0
        while ( count > 0 ):
            time.sleep( 60 )
            urlList, start = metaSearch.executeQuery( db, query, count, start )

            for url in urlList:
                webPage, headers = spider.fetch( url )

                if ( webPage ):
                    storePageAndHeader( url, webPage, headers, itemName, itemType )

                    count -= 1
                    if ( count <= 0 ):
                        break


def buildPositionalIndex ( ):
    """
    Opens every file in data/clean directory and creates the positional index.
    """
    print( "Building positional index..." )

    global pIndex
    global docWeight
    global queryWeight
    global numDocs
    numDocs = 0

    pIndex = dict( )

    dirs = os.listdir('data/clean')

    for file in dirs:

        if file == '.DS_Store':
            continue #bypass first junk value
        #for cleanFileName in os.listdir( 'data/clean' ):
        numDocs += 1
        stemNum = 0
        cleanFile = open('data/clean/'+file)
        file = file.strip('.txt')

        #with open( 'data/clean/' + cleanFileName ) as cleanFile:
        #cleanFileName = cleanFileName.strip( '.txt' )
        for stem in cleanFile:
            stem = stem.strip( )
            if stem not in pIndex:
                pIndex[stem] = dict( )
            if file not in pIndex[stem]:
                pIndex[stem][file] = list( )
                pIndex[stem][file].append(0)
            pIndex[stem][file].append( stemNum )
            stemNum += 1


    # If we want to print the index, uncomment code below.
    '''
    for stem in pIndex:
      print( stem + ":" )
      for stemDoc in pIndex[stem]:
        print( "\t" + stemDoc + ":", end=" " )
        stemLocations = ""
        for stemLoc in pIndex[stem][stemDoc]:
          stemLocations += str( stemLoc ) + ', '
        stemLocations = stemLocations.strip( ', ' )
    '''

def docLTC ( ):
    docLen = dict()

    #1st Pass - Accumalate Raw Weight, for each doc D for all terms T
    for term in pIndex:
        docFreq = len(pIndex[term])

        inverseDocFreq = math.log(numDocs/docFreq)
        for doc in pIndex[term]:
            termFreq = 1+math.log(len(pIndex[term][doc])-1)
            Weight = termFreq * inverseDocFreq
            pIndex[term][doc][0] = Weight
            if doc not in docLen:
                docLen[doc] = Weight*Weight
            else:
                docLen[doc] += Weight*Weight

    #2nd Pass - Normalize Weight, for each doc D for all terms T
    for term in pIndex:
        for doc in pIndex[term]:
            magnitude = math.sqrt(docLen[doc])
            pIndex[term][doc][0] /= magnitude


def docNNN ( ):
    for term in pIndex:
        for doc in pIndex[term]:
            termFreq = len(pIndex[term][doc])-1
            pIndex[term][doc][0] = termFreq

def queryLTC(text):
    qMag = 0.0
    qWeight = dict()
    counts = dict()
    textList = text.split()
    for term in textList:
        if term not in counts:
            counts[term] = 1
        else:
            counts[term] +=1

    for term in textList:
        docFreq = len(pIndex[term])
        termFreq = 1+math.log(counts[term])
        inverseDocFreq = math.log(numDocs/docFreq)
        weight = termFreq * inverseDocFreq
        qMag += weight*weight
        qWeight[term] = weight

    for term in textList:
        qWeight[term] /= math.sqrt(qMag)

    return qWeight


def queryNNN(text):
    counts = dict()
    textList = text.split()
    for term in textList:
        if term not in counts:
            counts[term] = 1
        else:
            counts[term] +=1
    return counts

def scoring(qWeights, totalOrdering = False):
    scores = dict()

    '''
    did = 18
    didScore = 0
    for t in pIndex:
        for d in pIndex[t]:
            if str(d) == str(did):
                didScore += pIndex[t][d][0]*pIndex[t][d][0]
    print("DID Score:"+str(didScore))


    '''
    totalOrdering = True
    if totalOrdering:
        for i in range(390):
            scores[str(i+1)] = 0.00000001*random.random()

    for term in qWeights:
        for docID in pIndex[term]:

            if docID not in scores:
                scores[docID] = pIndex[term][docID][0] * qWeights[term]
            else:
                scores[docID] += pIndex[term][docID][0] * qWeights[term]
    scores = sorted(scores.items(), key=operator.itemgetter(1), reverse=True)

    return scores

def performanceTesting ( ):
    """
    Method to perform evaluation of Search Engines performance
    :param None
    :return: Output to console evaluation metrics results (avgPrec, rPrec, Prec@N, AUC)
    """

    fileList = ['book.txt', 'movie.txt', 'music.txt']

    queryObject = Query(pIndex)

    queryList = textFileQuery(fileList)
    textDocWeighting()
    textQueryWeighting()

    itemCount = 1
    total10P = 0
    totalRP = 0
    totalMAP = 0
    totalAUC = 0
    for query in queryList:

        relevancyList = list()
        query = normalize(query)
        query = ' '.join(query) #Turn normalized word list into single normalized query string
        query = query.lower()

        if queryWeight == 'nnn':
            qWeights = queryNNN(query)
            cosines = scoring(qWeights)
        else:
            qWeights = queryLTC(query)
            cosines = scoring(qWeights)

        docIdResults = cosines
        numRel = 0

        for doc in docIdResults:
                docID = int(doc[0])
                itemID =  db.lookupItemId(docID)
                if itemID == itemCount:
                    relevancyList.append(1)
                    numRel += 1
                else:
                    relevancyList.append(0)
        itemCount += 1

        #shuffle(relevancyList)    #TO PERFORM RANDOM BASELINE EVALUATION, UNCOMMENT THIS LINE
        total10P += prec(relevancyList, 10)
        totalRP  += prec(relevancyList, numRel)
        totalMAP += meanAvgPrec(relevancyList)
        totalAUC += areaUnderCurve(relevancyList, cosines)

        #PERFORM CALCULATIONS
        #print("Total AUC (Pass: "+ str(itemCount-1) + ' ):\t'+ str(totalAUC))

    print("Prec@10: \t" + str(total10P/len(queryList)))
    print("Prec@R: \t" + str(totalRP/len(queryList)))
    print("MAP: \t\t" + str(totalMAP/len(queryList)))
    print("AUC: \t\t" + str(totalAUC/len(queryList)))


def prec(relevancyList, precNum):

    relevant = 0

    for i in range(precNum):
        if relevancyList[i] == 1:
            relevant +=1
    precision = relevant/precNum
    return precision

def meanAvgPrec(relevancyList):

    count = 0
    relevant = 0
    meanVals = 0
    for boolVal in relevancyList:
        if boolVal == 1:
            relevant +=1
            meanVals += relevant/(count+1)
        count += 1

    meanVals = meanVals / relevant

    return meanVals

def areaUnderCurve(relevancyList, cosines):

    totalHeight = 0
    numOnes = 0
    numZero  = 0

    for boolVal in relevancyList:
        if boolVal == 1:
            numOnes += 1
        else:
            numZero += 1
            totalHeight += numOnes
    ans = (totalHeight/numOnes)/numZero

    return ans
    """
    AUC = 0
    count = 0
    truePos = 0
    falsePos = 0
    trueNeg = 0
    falseNeg = 0
    specificity = 0
    sensitivity = 0
    for boolVal in relevancyList:
        if (boolVal == 1) and (cosines[count][1] > 0.00000001):
            truePos += 1
        elif (boolVal == 1) and (cosines[count][1] < 0.00000001):
            falsePos += 1
        elif (boolVal == 0) and (cosines[count][1] > 0.00000001):
            falseNeg +=1
        else:
            trueNeg +=1
        count += 1
    sensitivity = truePos / (truePos + falseNeg)
    specificity = trueNeg /(falsePos + trueNeg)
    falsePosRate = 1 - specificity
    if falsePosRate != 0:
        AUC = sensitivity / falsePosRate
    else:
        AUC = sensitivity / 1
    falsePosRate = falsePos / count
    truePosRate = truePos / count

    return AUC
    """


def textFileQuery( fileList ):
    queryList = list()
    for fileName in fileList:
        file = open("data/item/"+fileName, 'r+', encoding='utf-8')
        file = file.readlines()
        for line in file:
            queryList.append(line.rstrip('\n'))
    return queryList


def displayMenu ( ):
    print( "Command Options" )
    print( '  1)', "Token query" )
    print( '  2)', "AND query" )
    print( '  3)', "OR query" )
    print( '  4)', "Phrase query" )
    print( '  5)', "Near query" )
    print( '  6)', "QUIT" )
    print( )

    return getNumber( "Please type a number (1-6): " )

def displayWeightMenu():
    print("Weighting Options")
    print( '  1)', "nnn")
    print( '  2)', "ltc")
    print( )
    return getNumber( "Please type a number (1-2): ")



def getNumber ( prompt ):
    """
    Prompts user until integer input has been entered.
    """

    retVal = 0
    try:
        retVal = int( input( prompt ) )
    except:
        print( "Not a number, try again." )
        retVal = getNumber( prompt )
    finally:
        return retVal


def getWord ( ):
    """
    Prompt user for text input, return first group from space delimiter.
    """
    word = input( "Please enter a query: " )
    word = normalize(word)
    return word

def normalize ( term ):
    """
    Tokenize and stem input term.
    """
    config = configurationLoader.loadJsonFile( 'configuration.json' )
    config = config['query']
    term    = tokenize( config['tokenizer'], term )
    stemmer = stemlib.constructStemmer( config['stemmer'] )

    result = list()
    for x in term:
        result.append(stemmer.stem(x))
    return result
    #return stemmer.stem( term )

def getPhrase():
    word = input("Please enter a phrase: ")
    return word


def displayResults ( docList , cosineList):
    """
    With a list of document integer keys, lookup information in database
    to display to user. While looking up information, build a dictionary
    of items that the results were based on to display popular results in
    query.
    """


    if docList == []:
        print( "\n\tNone" )
        return

    itemDict = dict( )
    docListSet = set(docList)
    cosineWeights = cosineList


    print('Top 3 URL Results: ')

    count = 0
    for doc in cosineList:
        if doc[0] in docListSet:
            if count < 3:
                url, docType, title = db.lookupCachedUrl_byId( int(doc[0]) )
                itemId              = db.lookupItemId ( int(doc[0]) )
                name, itemType      = db.lookupItem_byId( itemId )
                print( "\n" +  str(count+1) + ".\t" + title.strip( ) + '\t\tWeights:' + str(doc[1]))
                print( '\t' + url )
                print( '\t' + itemType + ":", name )
                count +=1
        else:
            continue

    for doc in docList:
        if doc not in itemDict:
            itemDict[doc] = 1
        else:
            itemDict[doc] += 1

    docList = dict(docList)
    itemDict = sorted(docList.items(), key=operator.itemgetter(1), reverse=True)
    print()
    print("Top 3 Item Results: ")
    resultDict = dict()
    for topResult in itemDict:
        topResultInt = topResult[0]
        topResultInt = int(topResultInt)
        itemID =            db.lookupItemId(topResultInt)
        name, itemType =    db.lookupItem_byId(itemID)
        if (itemType+":", name) not in resultDict:
            resultDict[itemType+":", name] = (1 * topResult[1])
        else:
            resultDict[itemType+":", name] += (1 * topResult[1])
    resultDict = sorted(resultDict.items(), key=operator.itemgetter(1), reverse=True)
    for x in range(3):
        print('\n'+ str(x+1) + '.\t' + str(resultDict[x][0]))
    print()


    ''' USED FOR BOOLEAN RETRIEVAL
    count = 0
    for doc in docList:
        count += 1
        url, docType, title = db.lookupCachedUrl_byId( int(doc) )
        itemId              = db.lookupItemId ( int(doc) )
        name, itemType      = db.lookupItem_byId( itemId )

        if name not in itemDict:
            itemDict[name]  = 1
        else:
            itemDict[name] += 1

        print( "\n" + str(count) + ".\t" + title.strip( ) )
        print( '\t' + url )
        print( '\t' + itemType + ":", name )

    popularity  = 0
    for itemName in itemDict:
        if itemDict[itemName] > popularity:
            popularity  = itemDict[itemName]

    popItemList = list( )
    for itemName in itemDict:
        if itemDict[itemName] == popularity:
            popItemList.append( itemName )

    print( 'Most popular items are', popItemList, "with a count of", popularity )
    '''

def textDocWeighting( ):
    global docWeight
    userChoice = 0
    print(" - Choose DOC method - ")
    userChoice = displayWeightMenu()
    if ( userChoice == 1):
        docWeight = 'nnn'
        docNNN()
    elif ( userChoice == 2):
        docWeight = 'ltc'
        docLTC()
    else:
        print("Please Enter a Number Between (1-2)")

def textQueryWeighting( ):
    global queryWeight
    userChoice = 0
    print(" - Choose QUERY method - ")
    userChoice = displayWeightMenu()
    if ( userChoice == 1):
        queryWeight = 'nnn'
    elif ( userChoice == 2):
        queryWeight = 'ltc'
    else:
        print("Please Enter a Number Between (1-2)")

def textBasedUi ( ):
    """
    Offers 6 options to user. Handles input errors.
    """

    userChoice = 0
    query = Query( pIndex )
    userInput = ""
    cosines = 0 #Value for list of cosine values for page ranking

    while userInput != 'quit':
        print("Enter a query, type (quit) to exit")
        userInput = getWord()
        userInput = ' '.join(userInput) #convert list of normalized words from user input into single string
        if queryWeight == 'nnn':
            print("Weighting Query: NNN")
            qWeights = queryNNN(userInput)
            cosines = scoring(qWeights)
        else:
            print("Weighting Query: LTC")
            qWeights = queryLTC(userInput)
            cosines = scoring(qWeights)
        if userInput != 'quit':
            displayResults(query.stringQuery(userInput), cosines)
    print("QUITTING")
    '''
    while ( userChoice != 6 ):
        userChoice = displayMenu( )
        if ( userChoice == 1 ):
            input = getWord()
            if queryWeight == 'nnn':
                print("Weighting Query: NNN")
                qWeights = queryNNN(input)
                cosines = scoring(qWeights)
            else:
                print("Weighting Query: LTC")
                qWeights = queryLTC(input)
                cosines = scoring(qWeights)
            displayResults( query.tokenQuery( input ) , cosines)
        elif ( userChoice == 2 ):
            inputOne = getWord()
            inputTwo = getWord()
            if queryWeight == 'nnn':
                print("Weighting Query: NNN")
                qWeights = queryNNN(inputOne+' '+inputTwo)
                cosines = scoring(qWeights)
            else:
                print("Weighting Query: LTC")
                qWeights = queryLTC(inputOne+' '+inputTwo)
                cosines = scoring(qWeights)
            displayResults( query.andQuery( inputOne, inputTwo ), cosines)
        elif ( userChoice == 3 ):
            inputOne = getWord()
            inputTwo = getWord()
            if queryWeight == 'nnn':
                print("Weighting Query: NNN")
                qWeights = queryNNN(inputOne+' '+inputTwo)
                cosines = scoring(qWeights)
            else:
                print("Weighting Query: LTC")
                qWeights = queryLTC(inputOne+' '+inputTwo)
                cosines = scoring(qWeights)
            displayResults( query.orQuery( inputOne, inputTwo ), cosines)
        elif ( userChoice == 4 ):
            inputOne = getWord()
            inputTwo = getWord()
            if queryWeight == 'nnn':
                print("Weighting Query: NNN")
                qWeights = queryNNN(inputOne+' '+inputTwo)
                cosines = scoring(qWeights)
            else:
                print("Weighting Query: LTC")
                qWeights = queryLTC(inputOne+' '+inputTwo)
                cosines = scoring(qWeights)
            displayResults( query.phraseQuery( inputOne, inputTwo), cosines)
        elif ( userChoice == 5 ):
            nearness = getNumber( "How near (number)?: " )
            inputOne = getWord()
            if queryWeight == 'nnn':
                print("Weighting Query: NNN")
                qWeights = queryNNN(inputOne+' '+inputTwo)
                cosines = scoring(qWeights)
            else:
                print("Weighting Query: LTC")
                qWeights = queryLTC(inputOne+' '+inputTwo)
                cosines = scoring(qWeights)
            displayResults( query.nearQuery( inputOne, inputTwo, nearness ), cosines)
        elif ( userChoice == 6 ):
            pass
        else:
            print( "Number was not between 1 and 6.")
        '''


def main ( ):
    """
    1. Load configuration file.
    2. Read command line.
    3. Init database.
    4. Build directory structure, ensuring it exists.
    5. Download fresh documents, or stem new clean files from raw dir.
    6. Build positional index.
    7. Run the text-based UI.
    """

    global config, args

    config = configurationLoader.loadJsonFile( 'configuration.json' )
    args   = configurationLoader.readCmdLine( )

    if ( args.delete ):
        print( 'Deleting cache and exiting' )
        if ( args.delete == 'clean' ):
            deleteDirectoryStructure( )
        elif ( args.delete == 'all' ):
            deleteDirectoryStructure( True )
        exit( 0 )

    global db
    db = WebDb( 'data/cache.db' )

    buildDirectoryStructure( )

    if ( args.restore ):
        restoreClean( )
    # Uncomment else statement if we need to download docs with meta search.
    # else:
    #   downloadFreshDocuments( )

    buildPositionalIndex( )

    ''' DEBUGGING LAB 4 FUNCTIONS
    #test_String = "duck duck goos"
    #queryWeights = queryLTC(test_String)
    #print(queryWeights)
    #docLTC()
    #print("calling: scoring")
    #scoring(queryWeights)
    '''


    textDocWeighting()
    textQueryWeighting()
    textBasedUi( )

    #performanceTesting()

if __name__=='__main__':
    main( )


