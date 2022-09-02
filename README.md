# Orthanc helper
Made in order to automate some stuff we do regularly on our local Orthanc server.

## Requirements
- Orthanc server - https://www.orthanc-server.com/
    - You need to setup on modalities and connect them
    - Enable remote access in the Orthanc config if you are not running this from Orthanc server
- pyorthanc - `pip install pyorthanc`

## How to use it?
- There is a `helper_test.py` file that shows basic usage
- You can either use `config.json` file for your credentials or you can type them manually

## What can it do?
There are detailed docstrings for all functions.

### Batch upload
- `upload_folder()` - finds all dicom files in a given folder and its subfolders and uploads them to your server. You can also upload zip files of studies.

## Study data
Mostly used for naming files when downloading.
- `get_study_details()` - returns patient's name, study time and study date for a given study id
- `get_studies_list()` - returns patient name, time and date of study and id for all studies found on server

## Copying from modality to a server
- `date_modality_to_server()` - copies studies done on a given date from a given modality onto your server
- `date_range_modality_to_server()` - same as above but for a given date range (useful for daily "backups")

## Copying to local machine
- `date_server_to_local()` - downloads studies done on a given date from your server to the machine that is running this
- `date_range_server_to_local()` - same as above but for a given date range
- `anon_study_server_to_local()` - anonymizes given study, downloads it as zip file and then deletes the anonymized version from Orthanc. Server still keeps the original version. Use "lastName^firstName" or just use one of them and then select from the list.

## Deleting on the server
- `delete_on_date()` - deletes studies done on a given date from your server
- `delete_date_range()` - same as above but for a given date range

We have a small server so we have to clean it regularly.
- `delete_all_studies()` - Please only use this if you are certain you don't need anything. I am not responsible if you delete any critical data.
