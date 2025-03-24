# Pacemaker CIB Analyzer

This is a Python script to parse and analyze Pacemaker's Cluster Information Base (CIB) XML file. 

It reads two template parameter files (`cib_resources.txt` and `cib_parameters_value.txt`) located in the same directory as the script and generates a detailed report of the resources and properties found in the CIB XML file. 

The script also checks if the resources adhere to best practice settings as defined in the parameter files.

The results print to the standard output as well as local file under the same folder.

**NOTE:** 

- The location of cib.xml is /var/lib/pacemaker/cib/cib.xml.

- cib.xml can also be retrieved from sosreport (Red Hat family) or crm report (previously hb_report in SUSE) log bundles.
  
  sosreport cib.xml location: \sos_commands\pacemaker\crm_report\\<node name\>

## Azure Pacemaker Best Practice public doc
[https://learn.microsoft.com/en-us/azure/sap/workloads/high-availability-guide-suse-pacemaker?tabs=msi](https://learn.microsoft.com/en-us/azure/sap/workloads/high-availability-guide-suse-pacemaker?tabs=msi)

https://learn.microsoft.com/en-us/azure/sap/workloads/sap-hana-high-availability?tabs=lb-portal%2Csaphanasr

https://learn.microsoft.com/en-us/azure/sap/workloads/high-availability-guide-suse?tabs=lb-portal%2Censa1

https://learn.microsoft.com/en-us/azure/sap/workloads/high-availability-guide-rhel-pacemaker?tabs=msi

https://learn.microsoft.com/en-us/azure/sap/workloads/sap-hana-high-availability-rhel?tabs=lb-portal


## Prerequisites

- Python 3.x
- The following files should be present in the same directory as the script:
  - `cib_resources.txt`
  - `cib_parameters_value.txt`

## Usage

1. Clone or download this repository.
2. Ensure you have the required files (`CIB.xml`, `cib_resources.txt`, `cib_parameters_value.txt`).
3. Place `cib_resources.txt` and `cib_parameters_value.txt` in the same directory as the script.
4. Run the script with Python:

    ```sh
    python3 cib_parser.py <path of cib.xml>
    ```
    
```
##########################################
#                                        #
#       Pacemaker CIB Analysis Report    #
#       From Azure Linux Team            #
#                                        #
##########################################

No 'external/sbd' type resources found.
No 'azure-lb' type resources found.
No 'azure-events-az' type resources found.
...
----------------------------------------
Pacemaker Resource Analysis:
Warning: SAPHana AUTOMATED_REGISTER is set to false instead of one of the best practice values: true.
Original line:             <nvpair name="AUTOMATED_REGISTER" value="false" id="rsc_SAPHana_HDP_HDB03-instance_attributes-AUTOMATED_REGISTER"/>

Warning: property priority-fencing-delay setting is missing. It should be set to one of the best practice values: 30.
Warning: fence_azure_arm pcmk_delay_max setting is missing. It should be set to one of the best practice values: 15.
Warning: rsc_colocation score setting is missing. It should be set to one of the best practice values: 4000, -5000.


Pacemaker Resource Analysis Done

```

## Example contents of `cib_resources.txt`

```
external/sbd
fence_azure_arm
azure-lb
azure-events
azure-events-az
IPaddr2
SAPHanaTopology
SAPHana
SAPHanaController
SAPInstance
Filesystem
```

## Example contents of `cib_parameters_value.txt`
```
property:stonith-enabled:true
property:stonith-timeout:144|900
property:concurrent-fencing:true|NULL
fence_azure_arm:pcmk_delay_max:15
fence_azure_arm:pcmk_monitor_retries:4
fence_azure_arm:pcmk_action_limit:3
fence_azure_arm:power_timeout:240
fence_azure_arm:pcmk_reboot_timeout:900
fence_azure_arm:operation:monitor:timeout:120
fence_azure_arm:operation:monitor:interval:3600
azure-lb:resource-stickiness:0|NULL
property:resource-stickiness:1000|5000|1|3
property:priority-fencing-delay:30|15
property:migration-threshold:5000|3
azure-lb:operation:monitor:timeout:20s|20
azure-lb:operation:monitor:interval:10s|10
azure-events-az:failure-timeout:120s
rsc_colocation:score:4000|-5000
rsc_st_azure:timeout:120
SAPInstance:resource-stickiness:5000
SAPInstance:migration-threshold:1
SAPHana:AUTOMATED_REGISTER:true
SAPHana:operation:promote:timeout:3600
SAPHana:operation:monitor:interval:60|61|59
SAPInstance:operation:monitor:timeout:60
SAPInstance:operation:monitor:interval:20|11
azure-events-az:failure-timeout:120s
azure-events-az:operation:monitor:interval:10s|10
Filesystem:operation:monitor:interval:20s|20
Filesystem:operation:monitor:timeout:40s|40
IPaddr2:operation:monitor:interval:10s|10
IPaddr2:operation:monitor:timeout:20s|20

```

There are 2 types of format:
```
[field1]:[field2]:[field3] 

[field1]:[field2]:[field3][field4]:[field5]
```

For type1 - regular resource and global properties:

[field1] controls the check behavior, it can be either

**[specific resource type]**:[property]:[value]

Or

**[property]**:[parameter]:[value]

**property**: These settings can control default behaviors for resources, operations, and other cluster-wide configurations.

Since there could be same property name under different types, using this way we can control and make it more accurate while parsing the xml file.

For type2 - check operation settings, e.g. timeout, interval

**Note**: If you are not quite sure, do not edit this manually, check with the author.

# linux_log_parser.py

This `linux_log_parser.py` script has inherited from `cluster_log_parser`, which was originally used to parse pacemaker specific activity log lines.

Now `linux_log_parser.py` is a framework user can define their own patterns for specific scenarios.

It searches the pattern strings in `<type>_pattern.txt` in the same directory, for scope files defined in `<type>_filelist.txt`, then saves the output to a file named <type>_{timestamp}.txt in the same directory where the script is run.

After extracting the matched lines, the script process each line, extract the timestamp and hostname, format the timestamp, and group the entries by hostname.

Finally it provides statistics on the occurrences of each pattern, group by hostname/hourly period.

**Usage**

Example for pacemaker scenario

```
python3 linux_log_parser.py -t pacemaker -d <target dir>

python3 linux_log_parser.py -h

Usage options:
  -h, --help            show this help message and exit
  -d DIRECTORY, --directory DIRECTORY
  -t TYPE, --type TYPE  Type of log patterns to use
  --days DAYS           Number of days to look back for log analysis (default is 60)

##########################################
#                                        #
#       Linux Log Analysis               #
#       From Azure Linux Team            #
#                                        #
##########################################

Report generated on: 2025-03-24 12:00:38 CST+0800


================================================================================
Error Statistics Report
================================================================================

================================================================================
Error Statistics for Hostname: node1
================================================================================

======= /var/log/messages =======

Pattern: "pacemaker-schedulerd.* due to" - 34 occurrences

[/var/log/pacemaker/pacemaker.log-20250222.gz]
2025-02-16 06:00 ~ 06:59 - 15 occurrences

[/var/log/pacemaker/pacemaker.log-20250223.gz]
2025-02-22 05:00 ~ 05:59 - 12 occurrences
2025-02-22 06:00 ~ 06:59 - 7 occurrences

Pattern: "Node .*is now lost" - 5 occurrences

[/var/log/pacemaker/pacemaker.log-20250222.gz]
2025-02-16 06:00 ~ 06:59 - 5 occurrences

```
