from blackduck.HubRestApi import HubInstance
import json
import csv
import argparse

username = "sysadmin"
password = "blackduck"
urlbase = "https://blackduck.local"
inactiveLog = r"c:\temp\inactive.csv"  #add a location to your CSV log file

parser = argparse.ArgumentParser("Enter a number of days since last logged?")
parser.add_argument("-d", "--days", dest="days", type=int, default=30,
                    help="Specify the number of days that a user has not logged in the console.")

args = parser.parse_args()

hub = HubInstance(urlbase, username, password, insecure=True)

last_login = hub.get_last_login(sinceDays=args.days)

print("********************************************")
print("Print every user who should be inactive.")
print("********************************************")
print("")
print(last_login) 
print("")
print("")

##################################################################################################################################
# 1) - If System Users (anonymous, sysadmin, blackduck_system, default-authenticated user) are in this list, remove them from it #
# 2) - Remove users who have never logged in before 
##################################################################################################################################

last_login['items'] = [x for x in last_login['items'] if x['username'] not in ('sysadmin', 'anonymous', 'blackduck_system', 'default-authenticated-user')] #1
last_login['items'] = [x for x in last_login['items'] if 'lastLogin' in x] #2

print("********************************************")
print("Filter List: Users never logged in and system users: anonymous, sysadmin, blackduck_system, default-authenticated user")
print("********************************************")
print("")
print(last_login['items']) 
print("")
print("")

#############################################################
# Create a new last-login list based on the remaining users #
#############################################################

new_last_login = last_login['items']

###############################################
# Move (href:) key/value pair outside of meta #
###############################################

for index in range(len(new_last_login)):
  d = new_last_login[index] # Fetch the Dictionary element
  _meta = d['_meta'] # Fetch _Meta Key
  href = _meta['href'] # Fetch href
  d['href'] = href # Add to Main List
  del _meta['href'] # Delete from _Meta


print("********************************************")
print("Print updated list ")
print("********************************************")
print("")
print(new_last_login)
print("")
print("")
 
#######################################################
# 1) deletes (lastLogin) and *(_meta) keypairs        #
# 2) remove the '/last-login' from the HREF URL value #
# 3) grab the user data from current user in loop     #
# 4) create json data set with updated info for user  #
# 5) deactivate user                                  #
# 6) print user update status                         #
#######################################################

header = ['username','first name', 'last name', 'last login']

with open(inactiveLog, "w+", newline='') as f:
  writer = csv.writer(f, delimiter=',')
  writer.writerow(header) # write the header

for i in range(len(new_last_login)):

    del new_last_login[i]['_meta'] #1
    #del new_last_login[i]['lastLogin'] #1
    new_last_login[i]['lastLogin'] #1
    new_last_login[i]['href'] = new_last_login[i]['href'].replace("/last-login", "") #2

    user_url = new_last_login[i]['href'] #3
    user_info = hub.get_user_by_url(user_url) #3
    
    #print ("")
    #print(user_info)
    #print ("")

    print ("***getting user data***")
    print ("")


    data_set = {"active" : False, "userName" :new_last_login[i]['username'],"firstName" :user_info['firstName'], "lastName" :user_info['lastName']} #4
    json_dump = json.dumps(data_set) #4
    update_json=json_dump #4
    
    #print(user_url)
    #print(json_dump)

    print ("***deactivating user***")
    print ("")
    
    updateuser = hub.update_user_by_url(user_url,update_json) #5
       
    print("Result for user:" + new_last_login[i]['username'])
    print(updateuser) #6

    log = [new_last_login[i]['username'], user_info['firstName'], user_info['lastName'], new_last_login[i]['lastLogin']]
    
    with open(inactiveLog, mode='a', newline='') as f:
      writer = csv.writer(f, delimiter=',')
      writer.writerow(log) #write the inactive user data
    
    i=i+1





    
    





