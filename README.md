# Pacemaker CIB Analyzer

This is a Python script to parse and analyze Pacemaker's Cluster Information Base (CIB) XML file. 

It reads two template parameter files (`cib_resources.txt` and `cib_parameters_value.txt`) located in the same directory as the script and generates a detailed report of the resources and properties found in the CIB XML file. 

The script also checks if the resources adhere to best practice settings as defined in the parameter files.

The results print to the standard output as well as local file under the same folder.

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
    python3 cib_parser.py
    ```

5. When prompted, enter the absolute path of the CIB XML file. If you press Enter, the script will look for `CIB.xml` in the current working directory.


## Example contents of `cib_resources.txt`

```
sbd
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
property:concurrent-fencing:true
fence_azure_arm:pcmk_delay_max:15
fence_azure_arm:pcmk_monitor_retries:4
fence_azure_arm:pcmk_action_limit:3
fence_azure_arm:power_timeout:240
fence_azure_arm:pcmk_reboot_timeout:900
global:resource-stickiness:1000
global:priority-fencing-delay:30
azure-lb:resource-stickiness:0
azure-events-az:failure-timeout:120s
rsc_colocation:score:4000|-5000
SAPInstance:resource-stickiness:5000
```

The format is as [field1]:[field2]:[field3]

For regular resource types:
[resource type]:[property]:[value]

For other types:

global: These settings can control default behaviors for resources, operations, and other cluster-wide configurations.

property: These settings typically control specific cluster properties that influence the overall cluster behavior and configuration.

Since there could be same property name under different types, using this way we can control and make it more accurate while parsing the xml file.
