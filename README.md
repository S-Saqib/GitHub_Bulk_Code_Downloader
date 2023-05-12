# GitHub_Bulk_Code_Downloader

Description:
This is a web based interface to provide bulk code download facility from github. It helps specify some search criteria and download source codes that satisfy them. This tool is developed leveraging the keyword matching capability of GitHub code search API, augmenting with gpt-3.5 turbo API for structural description to keyword generation, and introducing appropriate checks and delays to avoid violation of the API constraints automating the whole process. However, it is not deployed because using the gpt-3.5 turbo API would incur financial cost.

Prerequisite:
1. Python 3
2. Github Personal Access Token
3. OpenAI API Access Token

To Run the Website Locally:
1. Download the files/Clone the repository
2. Go to the directory where login.py is located
3. Create two directories named "2_APIResponses" and "4_SrcCodeFiles"
4. Create a file named "openai_auth_token" and put only your OpenAI access token in it.
5. Run the command: python login.py. It would create a web server at localhost, at port 5000
6. In the web browser go to 127.0.0.1:5000/login

How to Use the Website:
1. Enter your personal access token of github
2. Select the appropriate language and specify whether you want to search by keyword or by structural syntax. For example, suppose, you want to match C source files that use the structure "dynamic memory allocation". You can directly put it in the keywords field and specify that you want to search by Structural Syntax. Alternatively, if you know that some of the keywords associated with it are "malloc", "realloc", "free" etc., you can search by keyword and put these keywords separated by comma.
3. Specify the sizes of the source files you want to explore and the number of files you want to download.
4. Hit download and wait for some time.
5. Once the download is finished, you will be redirected to the download page mentioned how many files were downloaded and how long it took.
6. You an find the downloaded files in the "4_SrcCodeFiles" directory. Some intermediate metadata files are also generated in the project directory, which may be useful in case of any interruption in the process.
