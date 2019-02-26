####################################################
# Serenity(v2) Report Crawler                      #
# Created: 26 Dec 2018                             #
# author: Ashutosh Mishra                          #
# Used python3 with BeautifulSoup                  #
# Perpose: To Crawl the Serenity(v2) report "index.html"
# Required Params:
# -rd=Path/to/Serenity/Project
# (Expected Structure: */ProjectName/BuildNumber/SerenityReportContents)
# returns: OrderedDictionary                       #
#############################################################################################
# Example Usage:                                                                            #
# python SerenityCrawler.py --debug=False -rd="/Users/ashutosh/Downloads/SerenityReports"   #
#############################################################################################

#===================
# Import section
#===================
from bs4 import BeautifulSoup
from urllib.request import urlopen
import re, os, sys, collections, datetime, argparse
import random, string

#========================
# Global Variables/Envs
#========================
#This limit prevents infinite recursion
#from causing an overflow of the C stack and crashing Python.
sys.setrecursionlimit(10000)
# total tests
total_tests = []
# root directory to lookup for Crawling (as command line argument)
root_dir = ""
# Set the debug mode
debugger = True
# Identifier Keys
KEY_AUTO_PASS_COL = 'Automated_Pass'
KEY_AUTO_FAIL_COL = 'Automated_Fail'
KEY_AUTO_DYN_COL = 'Automated_'

KEY_MAN_PASS_COL = 'Manual_Pass'
KEY_MAN_FAIL_COL = 'Manual_Fail'
KEY_MAN_DYN_COL = 'Manual_'

KEY_TOTAL_PASS_COL = 'Total_Pass'
KEY_TOTAL_FAIL_COL = 'Total_Fail'
KEY_TOTAL_DYN_COL = 'Total_'

KEY_FILE_NAME_TO_CRAWL = 'index.html'
KEY_PROJECT_NAME = 'Project_Name'
KEY_JENKINS_JOB_NUMBER = 'Build_Number'
KEY_REPORT_LOCATION = 'Location'
KEY_TEST_DATE = 'Test_Date'
KEY_UNIQUE_COL_NAME = 'Unique_Col_Name'

#========================
# internal debugger
#========================
def log(msg):
    if debugger:
        print("[DEBUG] :: {}".format(msg))

#############################################
# collectFiles() menthod
#############################################
def collectIndexFiles():
    """
    Loops across the root directory to fetch the index.html locations
    :return: A list containing location of all the files
    """
    # Debug
    log("Searching for index files ... ")
    # Index files list
    index_files = []
    for root, dirs, files in os.walk(root_dir, topdown=True):
        for file_name in files:
            # For the Serenity report index file
            # If the index file has been find but not under any library like datatables, jqueryui, etc, then collect it.
            if KEY_FILE_NAME_TO_CRAWL in file_name and 'datatables' not in root and 'jqueryui' not in root and 'JMeter' not in root:
                index_files.append(os.path.join(root, file_name))
    # Debug
    log(" Collected list of index files ... ")
    log(index_files)
    return index_files

#############################################
# getProjectMeta() method
#############################################
def getProjectMeta():
    """
    Uses the index.html file location to fetch details like project name and job number
    :param delete_mode: for the deletion of the reports (only last 20 report to be kept)
    :return: a list of dicts containing info about each index file.
    """
    # Project meta list
    project_meta = []
    all_files = collectIndexFiles()
    log("Iterating through index files ...")

    for file in all_files:
        log("    Crawling started for : {} ".format( str(file) ))
        file = file.replace("\\", '/')
        # Create a dictionary for the project meta(Name, jenkins build, report location)
        test_data_dict = {}
        # Split the projectName, BuildName, Location of the report
        test_data_dict[KEY_PROJECT_NAME] = str(file).split('/')[-3]
        test_data_dict[KEY_JENKINS_JOB_NUMBER] = str(file).split('/')[-2]
        test_data_dict[KEY_REPORT_LOCATION] = file
        # Add the above detail to the list
        project_meta.append(test_data_dict)

    # Log the meta list
    log('Collected Project Meta ::')
    for meta in project_meta:
        log('    > Name: {}, Build: {}, Location: {}'.format(meta[KEY_PROJECT_NAME], meta[KEY_JENKINS_JOB_NUMBER], meta[KEY_REPORT_LOCATION]) )

    # Return the meta list
    return project_meta

#############################################
# getProjectNames() method
#############################################
def getProjectNames():
    """
    :return: a list of all the Project names based on the directories
    """
    # It will only collect project Name (from the getProjectMeta() method)
    project_names = [];
    # Loop through the test details dictionary
    for test_data in getProjectMeta():
        if not test_data[KEY_PROJECT_NAME] in project_names:
            project_names.append(test_data[KEY_PROJECT_NAME])
    return project_names

#############################################
# scrapTheFile(test_detail) method
#############################################
def scrapTheFile(test_detail):
    """
    Extracts relevant data from each index.html file
    Initializes the database and stores the results into it.
    :param test_detail:
    """
    # Create Ordered dictionary for final formatted data
    row_dict = collections.OrderedDict()
    summary_result_dict = collections.OrderedDict()
    # List for scenarios outcome [pass, fail, pending, ignored, skipped, compromised]
    listForScenarios = []

    # Set the absolute index page location, which will be crawled
    html_page = urlopen("file:///" + test_detail[KEY_REPORT_LOCATION])
    # Initializes the BeautifulSoup for this report html Page
    soup = BeautifulSoup(html_page, "html.parser")

    try:
        #1: Extract the Date and time
        # find the date and time (report creation DD-MM-YYYY HH:MM)
        test_date = re.search(r'\d{2}-\d{2}-\d{4}\s\d{2}:\d{2}', soup.find("span", "date-and-time").text).group()
        date = datetime.datetime.strptime(test_date, "%d-%m-%Y %M:%S")
        # Final datetime
        date = date.strftime("%m/%d/%y %H:%M:%S")

        # 2: Extracting the build number based on the COLON ':' in project name.
        # Example:: [ProjectName_X: 11.01.1 BUILD-100, the build would be ' 11.01.1 BUILD-100' ]
        report_title = str(soup.find("span", 'projectname').text)
        build_number = str(soup.find("span", 'projectname').text).partition(":")[2].strip()

        # 3: Extract the test summary detail
        log(":::::::::: PROCESSING Scenario outcomes...")
        summary_table = soup.find("table", {"class": "table"})
        t_body = summary_table.find('tbody')
        rows = t_body.find_all('tr')
        row_c = col_c = 0
        for row in rows:
            cols=row.find_all('td')
            cols=[td.text.strip() for td in cols]
            log(cols)
            listForScenarios.append(cols)
            #####################

        # Process the collected data
        # Create an unique name for the entry [testName + underscore + testDate]
        # replacing all the spaces with underscores
        unique_col = (report_title + "_" + test_date).replace(' ', '_').strip()

        row_dict = extractAndRenderTheData(listForScenarios ,row_dict)

        # Set the extracted fields into final data
        row_dict[KEY_PROJECT_NAME] = test_detail[KEY_PROJECT_NAME]
        row_dict[KEY_JENKINS_JOB_NUMBER] = int(test_detail[KEY_JENKINS_JOB_NUMBER])
        row_dict[KEY_REPORT_LOCATION] = test_detail[KEY_REPORT_LOCATION]
        row_dict[KEY_UNIQUE_COL_NAME] = unique_col
        row_dict[KEY_TEST_DATE] = date

        # Final Output
        # Final formatted data for each Automation reports
        summary_result_dict[test_detail[KEY_PROJECT_NAME]] = row_dict

        # TODO: Store the following data
        print('Final Data::')
        print(summary_result_dict)
        print('\n')
    except Exception as e:
        log(" There was an error while extracting the report for Location: {}".format(loc))
        print(str(e))

######## RANDOM STRING GENERATION #########
# NNGExperimental
def randomword(length):
   letters = string.ascii_lowercase
   return ''.join(random.choice(letters) for i in range(length))
############################################

############################################
# extractAndRenderTheData(columnList)
############################################
def extractAndRenderTheData(datalists, data):
    """
    A method which extract the data from the list and form a dictionary.
    :param columnList
    :return data
    """
    record = data

    # Check the list element count for the first row
    totalColumns = 0
    log("Detecting the columns ....")
    for list in datalists:
        if len(list) == 3:
            totalColumns = 1
        else:
            totalColumns = 3
        break;

    # If One column then Assume 0 for other columns.
    if totalColumns == 1:
        log('    1 Column found: Only Automated Tests are present')
        for list in datalists:
        #SAMPLE:: ['Passing', '1', '100%']
            if len(list) >= 3:
                if str(list[0]) == 'Passing':
                    record[KEY_AUTO_PASS_COL] = list[1]
                    record[KEY_MAN_PASS_COL]   = '0'
                    record[KEY_TOTAL_PASS_COL] = list[1]
                elif str(list[0]) == 'Failed':
                    record[KEY_AUTO_FAIL_COL] = list[1]
                    record[KEY_MAN_FAIL_COL]  = '0'
                    record[KEY_TOTAL_FAIL_COL]= list[1]
                else:
                    # Assuming Manual Column as ZERO
                    record[KEY_AUTO_DYN_COL+str(list[0])]  = list[1]
                    record[KEY_MAN_DYN_COL+str(list[0])]   = '0'
                    record[KEY_TOTAL_DYN_COL+str(list[0])] = list[1]
        # End of For
    # If Three columns and blank value then put 0 there.
    elif totalColumns == 3:
        # Split the list then process.
        log('    3 Column found: Both Automated/Manual Tests are present')
        for list in datalists:
        #SAMPLE:: ['Passing', '18', '26%', '0', '', '18', '26%']
            if len(list) >= 7:
                if str(list[0]) == 'Passing':
                    record[KEY_AUTO_PASS_COL] = list[1]
                    record[KEY_MAN_PASS_COL]   = list[3]
                    record[KEY_TOTAL_PASS_COL] = list[5]
                elif str(list[0]) == 'Failed':
                    record[KEY_AUTO_FAIL_COL]  = list[1]
                    record[KEY_MAN_FAIL_COL]   = list[3]
                    record[KEY_TOTAL_FAIL_COL] = list[5]
                else:
                    record[KEY_AUTO_DYN_COL+str(list[0])]  = list[1]
                    record[KEY_MAN_DYN_COL+str(list[0])]   = list[3]
                    record[KEY_TOTAL_DYN_COL+str(list[0])] = list[5]

    # Return the record
    return record
######

############################################
# update the serenity report resources
############################################
def addHomeNavToSerenityReport(file):
    """
    Add a navigation link for the home "/"
    """
    tobeModified = False
    output = []
    f_line = ''
    f = open(file, "r")
    for line in f:
        # Set the "/" route inplace of logo's "index.html"
        if '<div id="logo"><a href="index.html">' in line:
            tobeModified = True
            f_line = line.replace('<div id="logo"><a href="index.html">', '<div id="logo"><a href="/">')
        else:
            f_line = line

        # Save to the out put
        output.append(f_line)
    # Close the file now.
    f.close()

    # Write to a file
    if tobeModified:
        with open(file, "w") as f:
            for l in output:
                f.write(l)
    log('File Modified Successfully\n')
# End of function

##################################
# Application Initiation         #
##################################
if __name__ == "__main__":
    msg = "\n#########################################\n#   INITIATING SERENITY REPORT CRAWLER  #\n#########################################\n"
    #
    print(msg)

    # CLI argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument("-rd", "--root_dir", required=True, help="Root Directory for all the files.")
    parser.add_argument("-d", "--debug", help="Execute in debug mode (True or False)")
    args = parser.parse_args()

    # Check for the provided CLI parameters
    if not os.path.isdir(args.root_dir):
        print("Path \'{}\' does not exist. Please provide"
              "a correct path for the root directory.".format(args.root_dir))
        exit()
    else:
        root_dir = args.root_dir

    # Check for the debugger mode
    if (str(args.debug) == 'True' or str(args.debug) == 'TRUE' or str(args.debug) == 'true'):
        debugger = True
    else:
        debugger = False

    # Get the test details from the available reports
    test_info = getProjectMeta()
    print("Total available builds: {}\n ".format( len(test_info) ))

    # For each project, get the data
    for index in test_info:
        scrapTheFile(index)

    # Debug: End of the Crawling Program
    print("\n#########################################\n")
