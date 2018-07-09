# HUB REST API Python

Wrapper for common HUB API queries. 
Upon initialization Bearer tocken is obtained and used for all subsequent calls

Usage: 
```
    from bds_hub_api import HubInstance
    
    username="sysadmin"
    password="blackduck"
    urlbase="https://ec2-34-201-23-208.compute-1.amazonaws.com"
    
    hub = HubInstance(urlbase, username, password, insecure=True)
    
    projects = hub.get_projects()
```    

## Example: 

Find versions that have identical BOM and optionally delete redundant data

```
python3 duplicates.py
```

Set cleanup=True to remove redundant data

## Python 3 and requests package are required
