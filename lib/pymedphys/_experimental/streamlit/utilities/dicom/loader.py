# Copyright (C) 2021 Cancer Care Associates

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import BinaryIO, Sequence

from pymedphys._imports import pydicom
from pymedphys._imports import streamlit as st

# For using the pretty name printer. Probably worth a moving that
# function out into a utility. For another PR though :).
from pymedphys._experimental.streamlit.apps import sum_doses as _sum_doses


def dicom_file_loader(accept_multiple_files, stop_before_pixels):
    left_column, right_column = st.beta_columns(2)

    if accept_multiple_files:
        Files = Sequence[BinaryIO]
        file_string = "files"
    else:
        Files = BinaryIO
        file_string = "file"

    with left_column:
        st.write(f"## Upload DICOM {file_string}")
        files: Files = st.file_uploader(
            f"DICOM {file_string}", accept_multiple_files=accept_multiple_files
        )

    if not files:
        raise st.stop()

    try:
        files[0]
    except TypeError:
        # If the return from file uploader is not indexable
        files = [files]

    datasets = []
    for a_file in files:
        try:
            a_file.seek(0)
            dataset = pydicom.dcmread(
                a_file, force=True, stop_before_pixels=stop_before_pixels
            )
        except Exception as e:
            st.warning(
                f'Failed reading the file "`{a_file.name}`". The error was the following:'
            )
            st.error(e)
            st.stop()
            raise

        datasets.append(dataset)

    with right_column:
        st.write("## Details")
        patient_ids = set()
        for dataset in datasets:
            patient_id = dataset.PatientID
            if patient_id in patient_ids:
                continue

            patient_name = _sum_doses.get_pretty_patient_name_from_dicom_dataset(
                dataset
            )

            st.write(
                f"""
                * Patient ID: `{patient_id}`
                * Patient Name: `{patient_name}`
                """
            )

            patient_ids.add(patient_id)

    return datasets
