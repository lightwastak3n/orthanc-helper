import os
import json
import threading

from pyorthanc import Orthanc
from requests.exceptions import HTTPError


class Server():
    def __init__(self, server_url: str=None, username: str=None, password: str=None) -> None:
        """Constructor

        Parameters
        ----------
        server_url: str
            Orthanc server address
        username: str
            Username.
        password: str
            Password.
        """
        if not server_url:
            server_url, username, password = self.load_credentials()
        self.server = Orthanc(server_url)
        self.server.setup_credentials(username, password)

    def load_credentials(self) -> tuple:
        """
        Loads ORTHANC server url, username and password from the config file.

        Return
        ------
            Returns server url, username and password found in the config file.
        """
        with open('config.json', 'r') as config:
            data = json.load(config)
        server_url = data['server']['url']
        username = data['server']['username']
        password = data['server']['password']
        return server_url, username, password

    def upload_folder(self, folder_path: str, threads_no: int = 4) -> None:
        """
        Uploads all dicom files found in folder_path recursively to the dicom server.
        
        Parameters
        ----------
        folder_path: str
            Path to the folder that contains dicom files.
        threads_no: int
            Number of threads to use for uploading. 4 by default.
        """        
        dicom_files = []
        for path, subdirs, files in os.walk(folder_path):
            for name in files:
                dicom_files.append(os.path.join(path, name))

        def upload_instances(dicom_list):
            for dicom_file in dicom_list:
                with open(dicom_file, 'rb') as image:
                    self.server.post_instances(image.read())
                print(f"Uploaded {dicom_file}.")

        threads = []
        for i in range(threads_no):
            upload_files = dicom_files[i::threads_no]
            t = threading.Thread(target=upload_instances, args=(upload_files, ))
            t.start()
            threads.append(t)
            
        for thread in threads:
            thread.join()

        print(f"Uploaded {len(dicom_files)} dicom files found in {folder_path}.")

    def get_study_details(self, study_id: str) -> tuple:
        """
        Gets patients name, study time, study date from a specified study id.
        
        Parameters
        ----------
        study_id : str
            Unique id of the study.
    
        Return
        ------
        tuple : str, str, str
            tuple of patients name, study time (time_date), study date
            Formats: lastName_firstName (or the other way around depending on original input), hhmmss, yyyymmdd
        """
        study_info = self.server.get_study_information(study_id)
        p_name = study_info['PatientMainDicomTags']['PatientName']
        p_name = p_name.rstrip("^").replace("^","_")

        study_date = study_info['MainDicomTags']['StudyDate']
        study_time = study_info['MainDicomTags']['StudyTime']
        return p_name, study_time, study_date

    def date_modality_to_server(self, modality: str, date: str, server_name: str = "ORTHANC", threads_no: int = 2) -> None:
        """
        Downloads studies created on specified date and from specified modality to specified ORTHANC server.
        
        Parameters
        ----------
        modality: str
            Name of the modality to query and to download from.
        date : str
            Date on which patients studies were created. Format 'yyyymmdd'.
        server_name: str
            Name of your ORTHANC server. 'ORTHANC' by default.
        threads_no: int
            Number of threads to use for downloading. 2 by default.
        """
        d1 = '''{
        "Level" : "Study",
        "Query" : {
        "AccessionNumber" : "",
        "PatientBirthDate" : "",
        "PatientID" : "",
        "PatientName" : "",
        "PatientSex" : "",'''
        d2 = f'\n\t"StudyDate" : "{date}",'
        d3 = '''\n\t"StudyDescription" : ""
        }
        }'''
        search_data = json.loads(d1+d2+d3)
        result = self.server.query_on_modality(modality, data=search_data)
        query_id = result['ID']
        server_data = {'TargetAet': f"{server_name}"}
        answers = self.server.get_query_answers(query_id)

        def download_answer(index_list):
            for index in index_list:
                patient_name = self.server.get_content_of_specified_query_answer(query_id, index)['0010,0010']['Value']
                print(f"Downloading {patient_name} to {server_name}")
                self.server.send_resource_to_other_modality(query_id, index, server_data)

        threads = []
        print(f"{len(answers)} studies found on {date}. Downloading to {server_name}")
        for i in range(threads_no):
            index_list = answers[i::threads_no]
            t = threading.Thread(target=download_answer, args=(index_list, ))
            t.start()
            threads.append(t)
        for thread in threads:
            thread.join()
        print(f"Finished download {len(answers)}")

    def date_range_modality_to_server(self, modality: str, from_date: str, to_date: str, server_name: str = "ORTHANC", thread_no: int = 2) -> None:
        """
        Downloads studies created on specified date range and from specified modality to specified ORTHANC server.
        
        Parameters
        ----------
        modality: str
            Name of the modality to query and to download from.
        from_date : str
            Start of the date range. Format 'yyyymmdd'.
        to_date: str
            End of the date range. Format 'yyyymmdd'
        server_name: str
            Name of your ORTHANC server. 'ORTHANC' by default.
        threads_no: int
            Number of threads to use for downloading. 2 by default.
        """
        self.date_modality_to_server(modality, f"{from_date}-{to_date}", server_name, thread_no)
        print("Finished downloading all studies between {from_date} and {to_date} from {modality} to {server_name}.")

    def date_server_to_local(self, date: str, download_path: str, threads_no: int = 2) -> None:
        """
        Downloads studies (from ORTHANC server to local machine) that were created on a specified date and stores them as zip files.
        
        Parameters
        ----------
        date : str
            Date on which studies were created. Format 'yyyymmdd'.
        download_path: str
            Folder to which to download studies.
        threads_no: int
            Number of threads to use for downloading. 2 by default.
        """
        d1 = '''{
                    "Level" : "Study",
                    "Query" : {
                        "Modality" : "",'''
        d2 = f'''\n\t"StudyDate" : "{date}",'''
        d3 = '''\n\t"PatientID" : "*"
                    }
                    }'''
        search_data = json.loads(d1+d2+d3)
        studies_ids = self.server.c_find(search_data)


        def download_studies(studies):
            for study_id in studies:
                p_name, study_time, study_date = self.get_study_details(study_id)
                file_name = f"{p_name}_{study_time}.zip"
                file_path = os.path.join(download_path,file_name)
                print(f"Downloading {file_name}.")
                with open(file_path, 'wb') as study_zip:
                    study_zip.write(self.server.get_study_zip_file(study_id))
        
        threads = []
        for i in range(threads_no):
            studies = studies_ids[i::threads_no]
            t = threading.Thread(target=download_studies, args=(studies, ))
            t.start()
            threads.append(t)
        for thread in threads:
            thread.join()
        print(f"Finished downloading {len(studies_ids)} studies.")

    def date_range_server_to_local(self, from_date: str, to_date: str,  download_path: str, thread_no: int = 2) -> None:
        """
        Downloads studies (from ORTHANC server to local machine) that were created between specified date range.
        
        Parameters
        ----------
        afrom_date : str
            Start of the date range. Format 'yyyymmdd'.
        to_date: str
            End of the date range. Format 'yyyymmdd'
        download_path: str
            Folder to which to download studies.
        threads_no: int
            Number of threads to use for downloading. 2 by default.
        """
        self.date_server_to_local(f"{from_date}-{to_date}", download_path)
        print(f"Finished downloading all studies between {from_date} and {to_date} to {download_path}.")

    def delete_on_date(self, date: str) -> None:
        """
        Deletes studies done on a specified date.
        
        Parameters
        ----------
        date : str
            Date on which studies were created. Format 'yyyymmdd'.
        """

        d1 = '''{
                    "Level" : "Study",
                    "Query" : {
                        "Modality" : "",'''
        d2 = f'''\n\t"StudyDate" : "{date}",'''
        d3 = '''\n\t"PatientID" : "*"
                    }
                    }'''
        search_data = json.loads(d1+d2+d3)
        studies_ids = self.server.c_find(search_data)
        total = 0
        for study_id in studies_ids:
            p_name, study_time, study_date = self.get_study_details(study_id)
            print(f"Deleting {p_name}-{study_date}-{study_time}.")
            self.server.delete_study(study_id)
            total += 1
        print(f"Done. Deleted {total} studies done on {date}.")

    def delete_date_range(self, from_date: str, to_date: str) -> None:
        """
        Deletes studies that were created between specified date range.
        
        Parameters
        ----------
        from_date : str
            Start of the date range. Format 'yyyymmdd'.
        to_date: str
            End of the date range. Format 'yyyymmdd'
        """
        self.delete_on_date(f"{from_date}-{to_date}")

    def get_studies_list(self) -> list:
        """
        Gets details of all the studies that are on the server.
        
        Returns
        ----------
        studies_data : list
            2d list (list of lists) that contains [patients name, study time (hhmmss), study date (yyyymmdd), study id]
        """
        studies_ids = self.server.get_studies()
        studies_data = []
        for id in studies_ids:
            p_name, study_time, study_date = self.get_study_details(id)
            studies_data.append([p_name, study_time, study_date, id])
        return studies_data

    def anon_study_server_to_local(self, patient_name: str, download_path: str) -> None:
        """
        Takes patient's name and gives all studies found with that name. After you choose which study you wish to download it will
        anonymizes study, download it as zip file and then delete it from the server.
        
        Parameters
        ----------
        patient_name : str
            String to use as a patient name to search for a study to anonymize. Use the form john^smith or smith^john.
        download_path: str
            The path to a folder in which to save anonymized zip file.
        """
        d1 = '''{
                    "Level" : "Study",
                    "Query" : {
                        "Modality" : "",'''
        d2 = f'\n\t"PatientName" : "*{patient_name}*"'
        d3 = '}}'
        search_data = json.loads(d1+d2+d3)
        studies_ids = self.server.c_find(search_data)
        studies_details = []
        for study_id in studies_ids:
            studies_details.append(self.get_study_details(study_id))
        
        print("Choose which study to anonymize.")
        for number, study in enumerate(studies_details):
            print(f"{number} - {study}.")
        choice = int(input("\nType the number of the study you wish to anonymize: "))
        target_id = studies_ids[choice]
        response = self.server.anonymize_study(target_id, {})
        print("Anonymized selected study.")

        anon_id = response["ID"]
        file_path = os.path.join(download_path, "Anonymized_patient")
        with open(file_path, 'wb') as study_zip:
            print(f"Downloading anonymized zip for {patient_name}.")
            study_zip.write(self.server.get_study_zip_file(anon_id))
        self.server.delete_study(anon_id)
        print("Study anonymized and deleted.")
    
    def delete_all_studies(self) -> None:
        """
        Deletes everything from the server.
        """
        print('WARNING!! This will delete everything from your server.')
        input('Press ENTER to continue...')
        studies = self.server.get_studies()
        to_delete = len(studies)
        for study_id in studies:
            self.server.delete_study(study_id)
            to_delete -= 1
            print(f"Deleted {study_id}. Left {to_delete} to delete.")
        print("Deleted everything.")
