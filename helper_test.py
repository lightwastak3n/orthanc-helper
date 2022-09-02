from orthanc_helper import Server

orthanc = Server()
orthanc.upload_folder("/home/sasa/Documents/DICOM/Test_patients/")

studies = orthanc.get_studies_list()
print(studies)
patient = studies[0][0].replace("_", "^")
orthanc.anon_study_server_to_local(patient, "/home/sasa/Downloads/")

orthanc.delete_all_studies()
