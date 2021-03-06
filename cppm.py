import requests, json, sys, os, argparse, time
from getpass import getpass
from configparser import ConfigParser
#from json2html import *
import urllib3
urllib3.disable_warnings()

#Define Colors for Printed Text to STDOUT
class bcolors:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def printstatus(rulenumber):
    print('Exporting Rule : '+str(rulenumber), end='\r')

def checkcredential():
    try:
        #Read config.ini file
        config_object = ConfigParser()
        config_object.read("cppm.ini")
        #Get the SERVER section
        SERVER = config_object["SERVER"]
    except:
        print("cppm.ini does not exist\nPlease provide details below!")
    global mgmt_host
    try:
        mgmt_host = SERVER["mgmthost"]
        if mgmt_host == "":
            raise
    except:
        mgmt_host = input("Check Point Management Host IP: ")
    global mgmt_port
    try:
        mgmt_port = SERVER["mgmtport"]
        if mgmt_port == "":
            raise
    except:
        mgmt_port = input("Port: ")
    global username
    try:
        username = SERVER["cpuser"]
        if username == "":
            raise 
    except:
        username= input("Username: ")
    global password
    try:
        password = SERVER["cppass"]
        if password == "":
            raise
    except:
        password=str(os.environ.get("cppass"))
        if password == "None":
            password = getpass("Password: ")
    global PolicyName
    try:
        PolicyName = SERVER["policyname"]
        if PolicyName == "":
            raise
    except:
        PolicyName = input("Policy Name:")
    return 1

def checkcredential1():
    global mgmt_host
    mgmt_host = str(os.environ.get("mgmthost"))
    global mgmt_port
    mgmt_port = str(os.environ.get("mgmtport"))
    global username
    username=str(os.environ.get("cpuser"))
    global password
    password=str(os.environ.get("cppass"))
    if mgmt_host == "None" or mgmt_port == "None" or username == "None" or password == "None":
        print("The following environment variables need to be set")
        print("mgmthost: {}".format(mgmt_host))
        print("mgmtport: {}".format(mgmt_port))
        print("cpuser: {}".format(username))
        print("cppass: {}".format(len(password)))
        return 0 
    else:
        return 1

def getnumberlist(input,typeofinput):
    result = []
    if typeofinput=="f":
        with open(input,"r") as f:
            line = f.readlines()
    else:
        line = input.split()
    for l in line:
        l=l.rstrip("\n")
        if "-" in l:
            list=l.split("-")
            assert (int(list[1])>int(list[0])),"list must be incremental"
            for i in range (int(list[0]),int(list[1])+1):
                result.append(int(i))
                i+=1
        elif "," in l:
            for i in l.split(","):
                result.append(int(i))
        elif l!="":
            result.append(l)
    return result

def getnamelist(input,typeofinput):
    result=[]
    if typeofinput=="f":
        with open(input,"r") as f:
            line = f.readlines()
    else:
        line = input.split(",")
    for l in line:
        l=l.rstrip("\n")
        if "," in l:
            for i in l.split(","):
                result.append(i)
        elif l!="":
            result.append(l)
    return result

def api_call(ip_addr, port, command, json_payload, sid):
    url = 'https://' + ip_addr + ':' + port + '/web_api/' + command
    if sid == '':
        request_headers = {'Content-Type' : 'application/json'}
    else:
        request_headers = {'Content-Type' : 'application/json', 'X-chkp-sid' : sid}
    r = requests.post(url,data=json.dumps(json_payload), headers=request_headers,verify=False)
    #print(r)
    return r.json()

def login(host, port, user,password,verbose=0):
    payload = {'user':user, 'password' : password}
    response = api_call(host, port, 'login',payload, '')
    if verbose: 
        print(f"Login Response {response}")
    return response["sid"]

def logout(user,password,sid):
    logout_result = api_call(mgmt_host, mgmt_port,"logout", {},sid)
    if logout_result["message"] == "OK":
        print("logout successfully")				
    #print("logout result: " + json.dumps(logout_result))	

def discardchanges(user,password,sid,verbose=0):
    answers = ['y', 'Y', 'N', 'n']
    answer = None
    while answer not in answers:
        print(f"{bcolors.YELLOW}\nCAUTION: {bcolors.CYAN}You are working on {bcolors.PURPLE}{PolicyName}{bcolors.ENDC}")
        answer = input("Are you sure to discard all changes?[Y|N] ")
        if answer in ['y','Y']:
            result = api_call(mgmt_host, mgmt_port,"discard", {},sid)
            if result["message"] == "OK":
                print("Discard changes successfully")				
            if verbose:
                print("Discard result: " + json.dumps(result))
        if answer in ['n','N']:
            print("Changes were not discarded")

def publishchanges(user,password,sid,verbose=0):
    answers = ['y', 'Y', 'N', 'n']
    answer = None
    while answer not in answers:
        print(f"{bcolors.YELLOW}\nCAUTION: {bcolors.CYAN}You are working on {bcolors.PURPLE}{PolicyName}{bcolors.ENDC}")
        answer = input("Are you sure to publish all changes?[Y|N] ")
        if answer in ['y','Y']:
            comment = input("Publish Comment: ")
            result = api_call(mgmt_host, mgmt_port,"set-session", {"description":comment},sid)
            #print(result)
            result = api_call(mgmt_host, mgmt_port,"publish", {},sid)
            if result["task-id"]:
                print(f"Published changes successfully. Task ID: {result['task-id']}")				
            if verbose:
                print("Publish result: " + json.dumps(result))
        if answer in ['n','N']:
            print("Changes were not published")			

def get_key(data,key1,key2):
    data1=data.get(key1)
    try:
        if key2 == "":
            return str(data1)
        else:
            if key2 not in data1:
                key2="name"	
            return str(data1.get(key2))
    except:
	    return "ERROR"

def getaccesslayers(server,port,sid):
    command = 'show-access-layers'
    layer = 'Network'
    host_data = {"limit" : 50, "offset" : 0, "details-level" : "standard"}
    result = api_call(server, port,command,host_data,sid)
    print(json.dumps(result))
    #formatted_table = json2html.convert(json=result)
    #print(formatted_table)

def getnatrule(server,port,rulelist,policy,sid,verbose=True):
    command = 'show-nat-rule'
    header=["Rule","Source","Destination","Port","NAT_Src","NAT_Dest","NAT_Services","Enabled","Install-on","Comment","Last-modify-time","Last-modifier","Creation-time","Creator","Enabled","UID"]
    listofrule=[]
    listofrule.append(header)
    for rulenumber in rulelist:
        host_data = {'rule-number':rulenumber, 'package':str(policy)}
        result = api_call(server, port,command, host_data ,sid)
        rule=[]
        if verbose:
            printstatus(rulenumber)
        #print(result)
        rule.append(rulenumber)
        # Original Source
        originalsource=""
        if result['original-source']['type'] == 'host':
            originalsource=result['original-source']['name'] + " - " + result['original-source']['ipv4-address']
        elif result['original-source']['type'] == 'group':
            originalsource="Group(" + result['original-source']['name'] + ")"
        elif result['original-source']['type'] == 'address-range':
            originalsource="Address Range (" + result['original-source']['name'] + ")"
        else:
            originalsource=result['original-source']['name']
        rule.append(originalsource) 

        #Original Destination
        originaldestination=""
        if result['original-destination']['type'] == 'group' or result['original-destination']['type'] == 'address-range':
            originaldestination=result['original-destination']['name']
        elif result['original-destination']['type'] == 'host':
            originaldestination=result['original-destination']['name'] + " - " + result['original-destination']['ipv4-address']
        rule.append(originaldestination) 

        #Original Service
        originalservice=""
        if result['original-service']['type'] == 'CpmiAnyObject':
            originalservice = result['original-service']['name']
        elif result['original-service']['type'] == 'service-tcp' or result['original-service']['type'] == 'service-udp':
            originalservice = result['original-service']['port'] + "/" + result['original-service']['type'][-3:]
        rule.append(originalservice) 
        
        #TranslatedSource
        translatedsource=""
        if result['translated-source']['type'] == 'host':
            translatedsource=result['method']+" ("+result['translated-source']['name'] + " - " + result['translated-source']['ipv4-address'] + ")"
        if result['translated-source']['type'] == 'Global':
            translatedsource=result['translated-source']['name']
        rule.append(translatedsource) 

        #TranslatedDestination
        translateddestination=""
        if result['translated-destination']['type'] == 'host':
            translateddestination=result['translated-destination']['name'] + " - " + result['translated-destination']['ipv4-address']
        if result['translated-destination']['type'] == 'Global':
            translateddestination=result['translated-destination']['name']
        rule.append(translateddestination) 
        rule.append(result['translated-service']['name']) 
        rule.append(result['enabled'])
        rule.append(result['install-on'][0]['name'])
        rule.append(result['comments']) 
        rule.append(result['meta-info']['last-modify-time']['iso-8601'])
        rule.append(result['meta-info']['last-modifier'])
        rule.append(result['meta-info']['creation-time']['iso-8601'])
        rule.append(result['meta-info']['creator'])
        rule.append(result['enabled'])
        rule.append(result['uid'])
        listofrule.append(rule)
    return listofrule

def getaccessrulebynumber(server,port,rulelist,layer,sid,verbose=True):
    #get total number of rule
    totalrule = getnumberofrule(server,port,layer,sid)
    #remove duplicates from list
    rulelist=list(dict.fromkeys(rulelist))
    #sort list 
    rulelist.sort()
    command = 'show-access-rule'
    header=["Rule","Name","Source","Destination","Services","VPN","Content","Action","Time","Track","Install On","Comment","Last-modify-time","Last-modifier","Creation-time","Creator","Enabled","Hit","UID"]
    listofrule=[]
    listofrule.append(header)
    for rulenumber in rulelist:
        if int(rulenumber) > totalrule:
            rulenumber = totalrule
        host_data = {'rule-number':rulenumber, 'layer':str(layer), 'show-hits':True}
        result = api_call(server, port,command, host_data ,sid)
        #print(f"Access Rule {result}\n")
        #print(f"Access Hits {result['hits']}")
        #print(f"Access Rule Source {result['source']}\n")
        #print(f"Access Rule Destination {result['destination']}\n")
        #print(f"Access Rule Service {result['service']}\n")
        #print(f"Access Rule VPN {result['vpn']}\n")
        rule=[]
        rule.append(rulenumber)
        if verbose:
            printstatus(str(rulenumber)+"    ")
        name=""
        if 'name' in result:
            name=result['name']
        rule.append(name)
        listofsource=""
        for r in result['source']:
            for k,v in r.items():
                if k == 'type' and v == 'host':
                    source = r['name'] + " - IP: " + r['ipv4-address'] + " + "
                if k == 'type' and v == 'network':
                    # print(k,": ",v,end='')
                    # print("name:",r['name'],end='')
                    # print("Net: ",r['subnet4'])
                    source = r['name'] + " - Net: " + r['subnet4'] + "/" + str(r['mask-length4']) + " + "
                elif k == 'type' and v == 'group':
                    # print(k,": ",v, end='')
                    # print("name:",r['name'])
                    source = r['name'] + " + "
                elif k == 'type' and v == 'CpmiAnyObject':
                    source = r['name'] + " + "
                elif k == 'type':
                    source = str(v) + " - " + r['name'] + " + "
            listofsource+=source
        if result['source-negate'] == False:
            rule.append(listofsource[:-3])
        else:
            rule.append("NOT ("+listofsource[:-3]+")")
        listofdestination=""
        for r in result['destination']:
            for k,v in r.items():
                if k == 'type' and v == 'host':
                    destination = r['name'] + " - IP: " + r['ipv4-address'] + " + "
                if k == 'type' and v == 'network':
                    destination = r['name'] + " - Net: " + r['subnet4'] + "/" + str(r['mask-length4']) + " + "
                elif k == 'type' and v == 'group':
                    destination = r['name'] + " + "
                elif k == 'type' and v == 'CpmiAnyObject':
                    destination = r['name'] + " + "
                elif k == 'type':
                    destination = str(v) + " - " + r['name'] + " + "
            listofdestination+=destination
        if result['destination-negate'] == False:
            rule.append(listofdestination[:-3])
        else:
            rule.append("NOT ("+listofdestination[:-3]+")")
        listofservice=""
        for r in result['service']:
            if r['name'] == "Any" or r['type']=="service-group":
                service=r['name'] + " + "
            elif r['name'] == "Any" or r['type']=="application-site":
                service=r['name'] + " + "
            elif r['type']=="service-tcp":
                service=r['name']+(" - TCP/") +r['port'] + " + "
            elif r['type']=="service-udp":
                service=r['name']+(" - UDP/") +r['port'] + " + "
            else:
                service=r['name'] + " + "
            listofservice+=service
        if result['service-negate'] == False:
            rule.append(listofservice[:-3])
        else:
            rule.append("NOT ("+listofservice[:-3]+")")
        rule.append(result['vpn'][0]['name'])
        rule.append(result['content'][0]['name'])
        rule.append(result['action']['name'])
        rule.append(result['time'][0]['name'])
        rule.append(result['track']['type']['name'])
        rule.append(result['install-on'][0]['name'])
        rule.append(result['comments'])
        rule.append(result['meta-info']['last-modify-time']['iso-8601'])
        rule.append(result['meta-info']['last-modifier'])
        rule.append(result['meta-info']['creation-time']['iso-8601'])
        rule.append(result['meta-info']['creator'])            
        rule.append(result['enabled'])
        rule.append(result['hits']['value'])
        rule.append(result['uid'])
        listofrule.append(rule)
        if result['action']['name'] == "Inner Layer":
            inlinelayer=result['inline-layer']['name']
            totalinlinerule=getnumberofrule(mgmt_host,mgmt_port,inlinelayer,sid)
            inlinerule=getaccessruleinline(mgmt_host,mgmt_port,rulenumber,totalinlinerule,inlinelayer,sid,0)
            for r in inlinerule:
                listofrule.append(r)
        if rulenumber == totalrule:
            break
    #Print notice if total rule is less than input list
    if totalrule < int(max(rulelist)):
        print(f"{bcolors.YELLOW}There are only {totalrule} rules{bcolors.ENDC}")
        time.sleep(2)
    return listofrule

def getaccessruleinline(server,port,parentrule,total,layer,sid,addheader,verbose=True):
    command = 'show-access-rule'
    header=["Rule","Name","Source","Destination","Services","VPN","Content","Action","Time","Track","Install On","Comment","Last-modify-time","Last-modifier","Creation-time","Creator","Enabled","Hit","UID"]
    listofrule=[]
    if addheader == 1:
        listofrule.append(header)
    for rulenumber in range(1,total+1):
        host_data = {'rule-number':rulenumber, 'layer':layer, 'show-hits':True}
        result = api_call(server, port,command, host_data ,sid)
        rule=[]
        subrulenumber=str(parentrule)+"."+str(rulenumber)
        rule.append(subrulenumber)
        if verbose:
            printstatus(subrulenumber)
        rule.append(get_key(result,'name',"")) #0
        listofsource=""
        for r in result['source']:
            for k,v in r.items():
                if k == 'type' and v == 'host':
                    source = r['name'] + " - IP: " + r['ipv4-address'] + " + "
                if k == 'type' and v == 'network':
                    source = r['name'] + " - Net: " + r['subnet4'] + "/" + str(r['mask-length4']) + " + "
                elif k == 'type' and v == 'group':
                    source = r['name'] + " + "
                elif k == 'type' and v == 'CpmiAnyObject':
                    source = r['name'] + " + "
                elif k == 'type':
                    source = str(v) + " - " + r['name'] + " + "
            listofsource+=source
        if result['source-negate'] == False:
            rule.append(listofsource[:-3])
        else:
            rule.append("NOT ("+listofsource[:-3]+")")
        listofdestination=""
        for r in result['destination']:
            for k,v in r.items():
                if k == 'type' and v == 'host':
                    destination = r['name'] + " - IP: " + r['ipv4-address'] + " + "
                if k == 'type' and v == 'network':
                    destination = r['name'] + " - Net: " + r['subnet4'] + "/" + str(r['mask-length4']) + " + "
                elif k == 'type' and v == 'group':
                    destination = r['name'] + " + "
                elif k == 'type' and v == 'CpmiAnyObject':
                    destination = r['name'] + " + "
                elif k == 'type':
                    destination = str(v) + " - " + r['name'] + " + "
            listofdestination+=destination
        if result['destination-negate'] == False:
            rule.append(listofdestination[:-3])
        else:
            rule.append("NOT ("+listofdestination[:-3]+")")
        listofservice=""
        for r in result['service']:
            if r['name'] == "Any" or r['type']=="service-group" or r['type']=="application-site":
                service=r['name'] + " + "
            elif r['type']=="service-tcp":
                service=r['name']+(" - TCP/") +r['port'] + " + "
            elif r['type']=="service-udp":
                service=r['name']+(" - UDP/") +r['port'] + " + "
            listofservice+=service
        if result['service-negate'] == False:
            rule.append(listofservice[:-3])
        else:
            rule.append("NOT ("+listofservice[:-3]+")")
        rule.append(result['vpn'][0]['name'])
        rule.append(result['content'][0]['name'])
        if result['action']['name'] == "Inner Layer":
            rule.append(result['action']['name'] + " - " + result['inline-layer']['name'])
        else:
            rule.append(result['action']['name'])
        rule.append(result['time'][0]['name'])
        rule.append(result['track']['type']['name'])
        rule.append(result['install-on'][0]['name'])
        rule.append(result['comments'])
        rule.append(result['meta-info']['last-modify-time']['iso-8601'])
        rule.append(result['meta-info']['last-modifier'])
        rule.append(result['meta-info']['creation-time']['iso-8601'])
        rule.append(result['meta-info']['creator'])            
        rule.append(result['enabled'])
        rule.append(result['hits']['value'])
        rule.append(result['uid'])
        listofrule.append(rule)
    return listofrule

def getnumberofrule(server,port,layer,sid,verbose=0):
    command = 'show-access-rulebase'
    host_data = {'name':layer}
    result = api_call(server, port,command, host_data ,sid)
    #formatted_table = json2html.convert(json=result)
    #print(formatted_table)
    if verbose:
        print(result)
    return int(result['total'])

def getapplicationsite(server,port,names,sid):
    command = 'show-application-site'
    header=["Name","Primary-Category","URL-List"]
    listofrule=[]
    listofrule.append(header)
    for name in names:
        host_data = {'name':name}
        result = api_call(mgmt_host, mgmt_port,command, host_data ,sid)
        rule=[]
        rule.append(name)
        rule.append(result['primary-category'])
        for r in result['url-list']:
            rule.append(r)
        listofrule.append(rule)    
    return listofrule

def whereused(server,port,names,sid):
    command = 'where-used'
    header=["No","Name","Column","Policy"]
    listofrule=[]
    listofrule.append(header)
    #print(names)
    for n in names:
        host_data = {'name':n}
        result = api_call(server, port,command, host_data ,sid)
        for r in result['used-directly']['access-control-rules']:
            rule=[]
            rule.append(r['position'])
            if 'name' in r['rule']:
                rule.append(r['rule']['name'])
            else:
                rule.append("")
            rule.append(r['rule-columns'])
            rule.append(r['layer']['name'])
            #print(rule)
            listofrule.append(rule)
    print(f"Number of rule found {len(listofrule)-1}") 
    time.sleep(2)   
    return listofrule

def getnetworkgroup(server,port,groups,sid):
    command = 'show-group'
    header=["GroupName","Name","Type","Address"]
    output=[]
    output.append(header)
    for groupname in groups:
        host_data = {'name':groupname}
        result = api_call(mgmt_host, mgmt_port,command, host_data ,sid)
        for r in result['members']:
            listofmembers=[]
            listofmembers.append(groupname)
            listofmembers.append(r['name'])
            listofmembers.append(r['type'])
            if r['type'] == 'host':
                listofmembers.append(r['ipv4-address'])
            if r['type'] == 'network':
                listofmembers.append(r['subnet4']+"/"+str(r['mask-length4']))
            if r['type'] == 'address-range':
                listofmembers.append(r['ipv4-address-first']+"-"+str(r['ipv4-address-last']))
            if r['type'] == 'group':
                subgroups=getsubgroup(server,port,groupname,r['name'],sid)
                for sg in subgroups:
                    listofmembers.append(sg)
            output.append(listofmembers)
    return output

def getsubgroup(server,port,parentgroup,group,sid):
    command = 'show-group'
    header=["GroupName","Name","Type","Address"]
    output=[]
    output.append(header)
    #for groupname in groups:
    host_data = {'name':group}
    print(group)
    result = api_call(mgmt_host, mgmt_port,command, host_data ,sid)
    for r in result['members']:
        listofmembers=[]
        listofmembers.append(parentgroup+"/"+group)
        listofmembers.append(r['name'])
        listofmembers.append(r['type'])
        if r['type'] == 'host':
            listofmembers.append(r['ipv4-address'])
        if r['type'] == 'network':
            listofmembers.append(r['subnet4']+"/"+str(r['mask-length4']))
        if r['type'] == 'address-range':
            listofmembers.append(r['ipv4-address-first']+"-"+str(r['ipv4-address-last']))
        output.append(listofmembers)
    return output

def printresult(data,printto,format,filename="output.txt",delimiter=";"):
    try:
        output=""
        if format=="csv":
            for line in data:
                for i,item in enumerate(line):
                    output+=str(item).replace("\n","")+str(delimiter)
                output+="\n"
        elif format=="txt" or format=="text":
            data.pop(0)
            for line in data:
                for i,item in enumerate(line):
                    output+=item+"\n"
                output+="\n"
        if printto == "stdout":
            lines=output.split("\n")
            for line in lines:
                if lines.index(line) == 0:
                    print(f"{bcolors.RED}{line}{bcolors.ENDC}")
                elif (lines.index(line) % 2) == 0:
                    print(f"{bcolors.BLUE}{line}{bcolors.ENDC}")
                else:
                    print(f"{bcolors.GREEN}{line}{bcolors.ENDC}")
        elif printto == "file":
            with open(filename,'w') as f:
                f.write(output)
            print("Save to {} successfully".format(filename))
    except Exception as e:
        print(e)

def disablerules(server,port,rulelist,layer,sid,verbose=0):
    #get total number of rule
    totalrule = getnumberofrule(server,port,layer,sid)
    if int(max(rulelist)) > int(totalrule):
        print(f"There are only {bcolors.YELLOW}{totalrule} rules\n{bcolors.RED}Due to impact of this function, please check rule list carefully{bcolors.ENDC}")
        return 0
    command = 'set-access-rule'
    listofrule=[]
    for rulenumber in rulelist:
        host_data = {'rule-number':rulenumber, 'layer':str(layer),'enabled':False}
        result = api_call(server, port,command, host_data ,sid)
        listofrule.append(rulenumber)
        if verbose:
            print(f"Rule {result}\n")
    return listofrule

def enablerules(server,port,rulelist,layer,sid,verbose=0):
    #get total number of rule
    totalrule = getnumberofrule(server,port,layer,sid)
    if int(max(rulelist)) > int(totalrule):
        print(f"There are only {bcolors.YELLOW}{totalrule} rules\n{bcolors.RED}Due to impact of this function, please check rule list carefully{bcolors.ENDC}")
        return 0
    command = 'set-access-rule'
    listofrule=[]
    for rulenumber in rulelist:
        host_data = {'rule-number':rulenumber, 'layer':str(layer),'enabled':True}
        result = api_call(server, port,command, host_data ,sid)
        listofrule.append(rulenumber)
        if verbose:
            print(f"Rule {result}\n")
    return listofrule

def removerules(server,port,rulelist,layer,sid,verbose=0):
    #Sort rule list last rule first as the last rule must be deleted first
    rulelist.sort(reverse=True)
    #get total number of rule
    totalrule = getnumberofrule(server,port,layer,sid)
    if int(max(rulelist)) > int(totalrule):
        print(f"There are only {bcolors.YELLOW}{totalrule} rules\n{bcolors.RED}Due to impact of this function, please check rule list carefully{bcolors.ENDC}")
        return 0
    command = 'delete-access-rule'
    listofrule=[]
    for rulenumber in rulelist:
        host_data = {'rule-number':rulenumber, 'layer':str(layer)}
        result = api_call(server, port,command, host_data ,sid)
        listofrule.append(rulenumber)
        if verbose:
            print(f"Deleted Rule {result}\n")
    listofrule.sort()
    return listofrule

def main():

    #try:
        #Menu
        parser=argparse.ArgumentParser(description='Check Point Policy Management')
        parser.add_argument('-w','--writefile',type=str,metavar='',help='File to write output to')
        group1=parser.add_mutually_exclusive_group(required=True)
        group1.add_argument('-f','--file',type=str,metavar='',help='File contains rule list')
        group1.add_argument('-r','--rule',type=str,metavar='',help='Rule list, dash or comma separted, no space')
        group=parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-n', '--nat',action='store_true', help='NAT Policy')
        group.add_argument('-s', '--security',action='store_true', help='Access Security')
        group.add_argument('-a', '--application',action='store_true', help='Access Application')
        group.add_argument('-as', '--applicationsite',action='store_true', help='Applicaiton Site')
        group.add_argument('-g', '--group',action='store_true', help='Network Group')
        group.add_argument('-ds', '--disablesecurity',action='store_true', help='Disable Security Rule')
        group.add_argument('-da', '--disableapplication',action='store_true', help='Disable Application Rule')
        group.add_argument('-es', '--enablesecurity',action='store_true', help='Enable Security Rule')
        group.add_argument('-ea', '--enableapplication',action='store_true', help='Enable Application Rule')
        group.add_argument('-rs', '--removesecurity',action='store_true', help='Remove Security Rule')
        group.add_argument('-ra', '--removeapplication',action='store_true', help='Remove Application Rule')
        group.add_argument('-wu', '--whereused',action='store_true', help='Find where the objects used')
        group.add_argument('-t', '--test',action='store_true', help='For Testing Purpose')
        args=parser.parse_args()

        #Test
        if args.test:
            #    getaccesslayers(mgmt_host,mgmt_port,sid)
            #layer = PolicyName + " Security"
            #result = disables(mgmt_host,mgmt_port,rulelist,layer,sid)
            print("Testing")
            sys.exit(1)
            
        #GET Rule List or Application Site Name List
        ## Get name list like application sites or group name from file -f 
        if args.applicationsite or args.group or args.whereused and args.file:
            rulelist=getnamelist(args.file,"f")
        ## Get name list like application sites or group name from cli -r
        elif args.applicationsite or args.group or args.whereused and args.rule:
            rulelist=getnamelist(args.rule,"r")
        ## Get number rule list from file -f
        elif args.file:
            rulelist=getnumberlist(args.file,"f")
        ## Get number rule list from cli -r
        elif args.rule:
            rulelist=getnumberlist(args.rule,"r")

        #CHECK if credential set  
        if checkcredential():
            try:
                sid = login(mgmt_host, mgmt_port, username,password)
            except Exception as e:
                print(e)
        else:
            print("Please set host and credential!")
            sys.exit(1)

        #DISABLE SECURITY RULE
        if args.disablesecurity:
            #getaccesslayers(mgmt_host,mgmt_port,sid)
            layer = PolicyName + " Security"
            #Get Policy Before Disabling
            #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
            #printresult(result,"stdout","csv")
            #Disable
            result = disablerules(mgmt_host,mgmt_port,rulelist,layer,sid)
            if not result:
                print("Nothing was changed")
            else:
                print("Disabled Security Rules: ",end="")
                for r in result:
                    print(f"{r}, ",end="")
                #Get Policy After Disabling
                #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
                #printresult(result,"stdout","csv")
                #Publish Changes
                publishchanges(username,password,sid)

        #DISABLE APPLICATION RULE
        if args.disableapplication:
            #   getaccesslayers(mgmt_host,mgmt_port,sid)
            layer = PolicyName + " Application"
            #Get Policy Before Disabling
            #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
            #printresult(result,"stdout","csv")
            #Disable
            result = disablerules(mgmt_host,mgmt_port,rulelist,layer,sid)
            if not result:
                print("Nothing was changed")
            else:
                print("Disabled Application Rules: ",end="")
                for r in result:
                    print(f"{r}, ",end="")
                #Get Policy After Disabling
                #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
                #printresult(result,"stdout","csv")
                #Publish Changes
                publishchanges(username,password,sid)

        #ENABLE SECURITY RULE
        if args.enablesecurity:
            #   getaccesslayers(mgmt_host,mgmt_port,sid)
            layer = PolicyName + " Security"
            #Get Policy Before Disabling
            #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
            #printresult(result,"stdout","csv")
            #Disable
            result = enablerules(mgmt_host,mgmt_port,rulelist,layer,sid)
            if not result:
                print("Nothing was changed")
            else:
                print("Enabled Security Rules: ",end="")
                for r in result:
                    print(f"{r}, ",end="")
                #Get Policy After Disabling
                #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
                #printresult(result,"stdout","csv")
                #Publish Changes
                publishchanges(username,password,sid)

        #ENABLE APPLICATION RULE
        if args.enableapplication:
            #   getaccesslayers(mgmt_host,mgmt_port,sid)
            layer = PolicyName + " Application"
            #Get Policy Before Disabling
            #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
            #printresult(result,"stdout","csv")
            #Disable
            result = enablerules(mgmt_host,mgmt_port,rulelist,layer,sid)
            if not result:
                print("Nothing was changed")
            else:
                print("Enabled Application Rules: ",end="")
                for r in result:
                    print(f"{r}, ",end="")
                #Get Policy After Disabling
                #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
                #printresult(result,"stdout","csv")
                #Publish Changes
                publishchanges(username,password,sid)

        #REMOVE SECURITY RULE
        if args.removesecurity:
        #   getaccesslayers(mgmt_host,mgmt_port,sid)
            layer = PolicyName + " Security"
            #Get Policy Before Disabling
            #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
            #printresult(result,"stdout","csv")
            #REMOVE
            result = removerules(mgmt_host,mgmt_port,rulelist,layer,sid)
            #If result = 0 (not successful), do nothing
            if not result:
                print("Nothing was changed")
            else:
                print("Removed Security Rules: ",end="")
                for r in result:
                    print(f"{r}, ",end="")
                #Get Policy After Disabling
                #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
                #printresult(result,"stdout","csv")
                #Publish Changes
                publishchanges(username,password,sid)
            

        #REMOVE APPLICATION RULE
        if args.removeapplication:
        #   getaccesslayers(mgmt_host,mgmt_port,sid)
            layer = PolicyName + " Application"
            #Get Policy Before Disabling
            #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
            #printresult(result,"stdout","csv")
            #REMOVE
            result = removerules(mgmt_host,mgmt_port,rulelist,layer,sid)
            #If result = 0 (not successful), do nothing
            if not result:
                print("Nothing was changed")
            else:
                print("Removed Application Rules: ",end="")
                for r in result:
                    print(f"{r}, ",end="")
                #Get Policy After Disabling
                #result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
                #printresult(result,"stdout","csv")
                #Publish Changes
                publishchanges(username,password,sid)

        #NAT RULE
        if args.nat:
            policy = PolicyName
            result=getnatrule(mgmt_host,mgmt_port,rulelist,policy,sid)
            #print(result)
            if not args.writefile:
                printresult(result,"stdout","csv")
            else:
                printresult(result,"file","csv",args.writefile)

        #SECURITY ACCESS RULE
        if args.security:
        #   getaccesslayers(mgmt_host,mgmt_port,sid)
            layer = PolicyName + " Security"
            result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
            if not args.writefile:
                printresult(result,"stdout","csv")
            else:
                printresult(result,"file","csv",args.writefile)

        #APPLICATION ACCESS RULE
        if args.application:
            layer = PolicyName + " Application"
            result = getaccessrulebynumber(mgmt_host,mgmt_port,rulelist,layer,sid)
            if not args.writefile:
                printresult(result,"stdout","csv")
            else:
                printresult(result,"file","csv",args.writefile)
        
        #Application Site
        if args.applicationsite:
            result=getapplicationsite(mgmt_host,mgmt_port,rulelist,sid)
            if not args.writefile:
                printresult(result,"stdout","csv")
            else:
                printresult(result,"file","txt",args.writefile)
        
        #Network Group
        if args.group:
            result=getnetworkgroup(mgmt_host,mgmt_port,rulelist,sid)
            if not args.writefile:
                printresult(result,"stdout","csv")
            else:
                printresult(result,"file","csv",args.writefile)
        
        #Where-Used
        if args.whereused:
            result=whereused(mgmt_host,mgmt_port,rulelist,sid)
            if not args.writefile:
                printresult(result,"stdout","csv")
            else:
                printresult(result,"file","csv",args.writefile)
        logout(username,password,sid)
    #except:
    #    print(f"Error: {sys.exc_info()[1]}")     
        	

def menu(command_line=None):
    parser = argparse.ArgumentParser('Blame Praise app')
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True
    access = subparsers.add_parser('access', help='Security Access Rule')
    access.add_argument(
        '--dry-run',
        help='do not blame, just pretend',
        action='store_true'
    )
    access.add_argument('name', nargs='+', help='name(s) to blame')
    praise = subprasers.add_parser('praise', help='praise someone')
    praise.add_argument('name', help='name of person to praise')
    praise.add_argument(
        'reason',
        help='what to praise for (optional)',
        default="no reason",
        nargs='?'
    )
    args = parser.parse_args(command_line)
    if args.debug:
        print("debug: " + str(args))
    if args.command == 'blame':
        if args.dry_run:
            print("Not for real")
        print("blaming " + ", ".join(args.name))
    elif args.command == 'praise':
        print('praising ' + args.name + ' for ' + args.reason)

if __name__ == '__main__':
    main()
