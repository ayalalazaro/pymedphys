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

import functools
import hashlib
import pathlib
import re
from typing import Dict

from pymedphys._imports import pydicom
from pymedphys._imports import streamlit as st

from pymedphys._streamlit import categories
from pymedphys._streamlit.utilities import config as st_config

CATEGORY = categories.PLANNING
TITLE = "Monaco Extend CT"


def main():
    config = st_config.get_config()

    site_directory_map = {}
    for site_config in config["site"]:
        site = site_config["name"]
        try:
            site_directory_map[site] = {
                "focal_data": site_config["monaco"]["focaldata"],
                "hostname": site_config["monaco"]["hostname"],
                "port": site_config["monaco"]["dicom_port"],
            }
        except KeyError:
            continue

    chosen_site = st.radio("Site", list(site_directory_map.keys()))
    directories = site_directory_map[chosen_site]

    focal_data = pathlib.Path(directories["focal_data"])
    dicom_export_directory = focal_data.joinpath("DCMXprtFile")

    # Caps or not within glob doesn't matter on Windows, but it does
    # matter on *nix systems.
    dicom_files = dicom_export_directory.glob("*.DCM")

    patient_id_pattern = re.compile(r"(\d+)_.*_image\d\d\d\d\d.DCM")
    patient_ids = list(
        {
            patient_id_pattern.match(path.name).group(1)
            for path in dicom_files
            if patient_id_pattern.match(path.name)
        }
    )

    chosen_patient_id = st.radio("Patient ID", patient_ids)

    function_cache = _get_function_cache(_load_exported_cts)

    st.write(function_cache)

    if len(function_cache) == 0:
        if not st.button("Load files"):
            st.stop()

    ct_datasets = _cached_load_exported_cts(dicom_export_directory, chosen_patient_id)

    patient_name = {header.PatientName for _, header in ct_datasets.items()}
    st.write(patient_name)


def _load_exported_cts(dicom_export_directory, patient_id):
    ct_dicom_files = list(dicom_export_directory.glob(f"{patient_id}_*_image*.DCM"))
    ct_datasets: Dict[str, pydicom.Dataset] = {
        path.name: pydicom.dcmread(path, force=True, stop_before_pixels=False)
        for path in ct_dicom_files
    }

    return ct_datasets


@functools.lru_cache()
def _get_function_cache(
    func,
    hash_funcs=None,
    max_entries=None,
    ttl=None,
):
    from streamlit.caching import _mem_caches

    func_hasher = hashlib.new("md5")
    st.hashing.update_hash(
        (func.__module__, func.__qualname__),
        hasher=func_hasher,
        hash_funcs=None,
        hash_reason=st.hashing.HashReason.CACHING_FUNC_BODY,
        hash_source=func,
    )

    st.hashing.update_hash(
        func,
        hasher=func_hasher,
        hash_funcs=hash_funcs,
        hash_reason=st.hashing.HashReason.CACHING_FUNC_BODY,
        hash_source=func,
    )

    cache_key = func_hasher.hexdigest()
    mem_cache = _mem_caches.get_cache(cache_key, max_entries, ttl)

    return mem_cache


_cached_load_exported_cts = st.cache(_load_exported_cts, allow_output_mutation=True)
