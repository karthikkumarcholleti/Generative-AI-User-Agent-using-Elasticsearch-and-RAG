"""
Maps a FHIR filename to an individual hospital key and its logical group.

get_hospital_key(filename) → individual facility key stored in source_hospital column
get_hospital_group(key)    → logical group for analytics (not stored in DB)
"""

import re

# ---------------------------------------------------------------------------
# Filename-pattern → individual hospital key
# Checked in order; first match wins.
# ---------------------------------------------------------------------------
_FILENAME_RULES = [
    # ── CCDA CCD network (fhir_output_TEST_ccd_{facility}_*) ───────────────
    (r"fhir_output_TEST_ccd_aspirushoughtonclinic",       "aspirus_houghton"),
    (r"fhir_output_TEST_ccd_aspirusironriverhospital",    "aspirus_ironriver"),
    (r"fhir_output_TEST_ccd_aspirusironwoodhospital",     "aspirus_ironwood"),
    (r"fhir_output_TEST_ccd_aspiruskeweenawhospital",     "aspirus_keweenaw"),
    (r"fhir_output_TEST_ccd_uphieaspirus",                "aspirus_uphie"),
    (r"fhir_output_TEST_ccd_uphealthsystem.marquette",    "uphsm_marquette"),
    (r"fhir_output_TEST_ccd_uphealthsystem.bell",         "uphsm_bell"),
    (r"fhir_output_TEST_ccd_uphsportagehealth",           "uphsm_portage"),
    (r"fhir_output_TEST_ccd_munisingmemorialhospital",    "uphsm_munising"),
    (r"fhir_output_TEST_ccd_osfst",                       "osf_stfrancis"),
    (r"fhir_output_TEST_ccd_schoolcraftmemorialhospital", "scmh_main"),
    (r"fhir_output_TEST_ccd_baragacountymemorialhospital","baraga_main"),
    (r"fhir_output_TEST_ccd_baycaremedicalcenter",        "baycare"),
    (r"fhir_output_TEST_ccd_bronsonbattlecreek",          "bronson"),
    (r"fhir_output_TEST_ccd_bshemergencydept",            "bsh"),
    (r"fhir_output_TEST_ccd_corewellhealth.east",         "corewell_east"),
    (r"fhir_output_TEST_ccd_corewellhealthsystem",        "corewell_system"),
    (r"fhir_output_TEST_ccd_corewellhealthtroyhospital",  "corewell_troy"),
    (r"fhir_output_TEST_ccd_dickinsoncountymemorialhospital", "dickinson"),
    (r"fhir_output_TEST_ccd_hfcccenterforfamilyhealth",   "henry_ford_cc"),
    (r"fhir_output_TEST_ccd_hfhnhenryfordhospital",       "henry_ford_main"),
    (r"fhir_output_TEST_ccd_hfjhjacksonhospital",         "henry_ford_jackson"),
    (r"fhir_output_TEST_ccd_hfmhmacombhospital",          "henry_ford_macomb"),
    (r"fhir_output_TEST_ccd_mclarenmacomb",               "mclaren_macomb"),
    (r"fhir_output_TEST_ccd_michiganmedicine",            "michigan_medicine"),
    (r"fhir_output_TEST_ccd_munsonhealthcarecharlevoix",  "munson_charlevoix"),
    (r"fhir_output_TEST_ccd_munsonmedicalcenter",         "munson_traverse"),
    (r"fhir_output_TEST_ccd_mymichiganmedicalcenter.westbranch", "mymichigan_westbranch"),
    (r"fhir_output_TEST_ccd_mymichigansault",             "mymichigan_sault"),
    (r"fhir_output_TEST_ccd_northottawacommunityhospital","north_ottawa"),
    (r"fhir_output_TEST_ccd_st\.johnhospital",            "st_john"),
    (r"fhir_output_TEST_ccd_st\.josephmercyhospitalannarbor", "st_joseph_mercy_aa"),

    # ── CCDA MEDREC files (fhir_output_TEST_{HOSP}_MEDREC_*) ───────────────
    (r"fhir_output_TEST_OSF_MEDREC",   "osf_main"),
    (r"fhir_output_TEST_UPHSM_MEDREC", "uphsm_main"),
    (r"fhir_output_TEST_SCMH_MEDREC",  "scmh_main"),

    # ── ADT files — facility-specific format (TEST_adt_{facility}_*) ─────────
    (r"TEST_adt_aspirushoughtonclinic",           "aspirus_houghton"),
    (r"TEST_adt_aspirusironriverhospital",         "aspirus_ironriver"),
    (r"TEST_adt_aspirusironwoodhospital",          "aspirus_ironwood"),
    (r"TEST_adt_aspiruskeweenawlauriumclinic",     "aspirus_laurium"),
    (r"TEST_adt_aspiruskeweenawhospital",          "aspirus_keweenaw"),
    (r"TEST_adt_baragacountymemorialhospital",     "baraga_main"),
    (r"TEST_adt_baycaremedicalcenter",             "baycare"),
    (r"TEST_adt_bronsonbattlecreek",               "bronson"),
    (r"TEST_adt_bshemergencydept",                 "bsh"),
    (r"TEST_adt_corewellhealthbutterworthhospital","corewell_butterworth"),
    (r"TEST_adt_corewellhealthsystem",             "corewell_system"),
    (r"TEST_adt_dickinsoncountymemorialhospital",  "dickinson"),
    (r"TEST_adt_hfcccenterforfamilyhealth",        "henry_ford_cc"),
    (r"TEST_adt_hfjhjacksonhospital",              "henry_ford_jackson"),
    (r"TEST_adt_hfhnhenryfordhospital",            "henry_ford_main"),
    (r"TEST_adt_mclarenmacomb",                    "mclaren_macomb"),
    (r"TEST_adt_medilodge",                        "medilodge"),
    (r"TEST_adt_munisingmemorialhospital",         "uphsm_munising"),
    (r"TEST_adt_munsonhealthcare",                 "munson_charlevoix"),
    (r"TEST_adt_munsonmedicalcenter",              "munson_traverse"),
    (r"TEST_adt_northcarepihp",                    "northcare"),
    (r"TEST_adt_osfst",                            "osf_stfrancis"),
    (r"TEST_adt_schoolcraftmemorialhospital",      "scmh_main"),
    (r"TEST_adt_st\.josephmercyhospital",          "st_joseph_mercy_aa"),
    (r"TEST_adt_uphealthsystem",                   "uphsm_marquette"),
    (r"TEST_adt_uphsportagehealth",                "uphsm_portage"),

    # ── ADT files — prefix-based format (TEST_{PREFIX}_A##_*) ──────────────
    # Match any HL7 event type (A01-A99): A0x admission/discharge, A1x, A2x, A3x ...
    (r"TEST_ASPIRH_",  "aspirus_main"),
    (r"TEST_OSF_A",    "osf_main"),
    (r"TEST_UPHSM_A",  "uphsm_main"),
    (r"TEST_SCMH_",    "scmh_main"),

    # ── ORU / LAB files ──────────────────────────────────────────────────────
    (r"TEST_Aspirus_LAB|TEST_ASPIRUS_LAB",          "aspirus_main"),
    (r"TEST_Baraga_LAB|TEST_BARAGA_LAB",            "baraga_main"),
    (r"TEST_Bell_LAB|TEST_BELL_LAB",                "uphsm_bell"),
    (r"TEST_Dickinson_LAB|TEST_DICKINSON_LAB",      "dickinson"),
    (r"TEST_HNJH.LAB",                              "henry_ford_jackson"),
    (r"TEST_Mackinac_LAB|TEST_MACKINAC_LAB",        "mackinac"),
    (r"TEST_Marquette_LAB|TEST_MARQUETTE_LAB",      "uphsm_marquette"),
    (r"TEST_Munising_LAB|TEST_MUNISING_LAB",        "uphsm_munising"),
    (r"TEST_OSF_LAB|TEST_Osf_LAB",                  "osf_main"),
    (r"TEST_Portage_LAB|TEST_PORTAGE_LAB",          "uphsm_portage"),
    (r"TEST_Schoolcraft_LAB|TEST_SCHOOLCRAFT_LAB",  "scmh_main"),

    # ── ORU / RADIOLOGY files ────────────────────────────────────────────────
    (r"TEST_Aspirus_RAD|TEST_ASPIRUS_RAD",          "aspirus_main"),
    (r"TEST_Marquette_RAD|TEST_MARQUETTE_RAD",      "uphsm_marquette"),
    (r"TEST_OSF_RAD|TEST_Osf_RAD",                  "osf_main"),
    (r"TEST_Schoolcraft_RAD|TEST_SCHOOLCRAFT_RAD",  "scmh_main"),
    (r"TEST_Baraga_RAD|TEST_BARAGA_RAD",            "baraga_main"),
    (r"TEST_Bell_RAD|TEST_BELL_RAD",                "uphsm_bell"),
    (r"TEST_Munising_RAD|TEST_MUNISING_RAD",        "uphsm_munising"),
    (r"TEST_Portage_RAD|TEST_PORTAGE_RAD",          "uphsm_portage"),
]

# Compile once at import
_COMPILED = [(re.compile(pat, re.IGNORECASE), key) for pat, key in _FILENAME_RULES]

# ---------------------------------------------------------------------------
# Group membership
# ---------------------------------------------------------------------------
_GROUPS = {
    "aspirus":       {"aspirus_houghton", "aspirus_ironriver", "aspirus_ironwood",
                      "aspirus_keweenaw", "aspirus_laurium", "aspirus_uphie", "aspirus_main"},
    "uphsm":         {"uphsm_marquette", "uphsm_bell", "uphsm_portage",
                      "uphsm_munising", "uphsm_main"},
    "osf":           {"osf_stfrancis", "osf_main"},
    "scmh":          {"scmh_main"},
    "baraga":        {"baraga_main"},
    "henry_ford":    {"henry_ford_main", "henry_ford_jackson",
                      "henry_ford_macomb", "henry_ford_cc"},
    "munson":        {"munson_traverse", "munson_charlevoix"},
    "mymichigan":    {"mymichigan_westbranch", "mymichigan_sault"},
    "corewell":      {"corewell_east", "corewell_butterworth", "corewell_system", "corewell_troy"},
}

# Build reverse map for O(1) lookup
_KEY_TO_GROUP = {}
for grp, keys in _GROUPS.items():
    for k in keys:
        _KEY_TO_GROUP[k] = grp


def get_hospital_key(filename: str) -> str:
    """Return the individual facility key for a given FHIR filename."""
    basename = filename.split("/")[-1]
    for pattern, key in _COMPILED:
        if pattern.search(basename):
            return key
    return "unknown"


def get_hospital_group(hospital_key: str) -> str:
    """Return the logical group for a hospital key (for analytics, not stored in DB)."""
    return _KEY_TO_GROUP.get(hospital_key, hospital_key)


if __name__ == "__main__":
    # Quick self-test with known filenames
    tests = [
        # CCDA CCD
        ("fhir_output_TEST_ccd_aspirushoughtonclinic_000000001_fhir.json", "aspirus_houghton"),
        ("fhir_output_TEST_ccd_uphealthsystem-marquette_000000073_fhir.json", "uphsm_marquette"),
        ("fhir_output_TEST_ccd_hfhnhenryfordhospital_000000001_fhir.json", "henry_ford_main"),
        # CCDA MEDREC
        ("fhir_output_TEST_OSF_MEDREC_000000740_fhir.json",  "osf_main"),
        ("fhir_output_TEST_SCMH_MEDREC_000000175_fhir.json",  "scmh_main"),
        # ADT prefix-based (all event types)
        ("TEST_ASPIRH_A04_000000250_fhir.json",               "aspirus_main"),
        ("TEST_OSF_A04_000000810_fhir.json",                  "osf_main"),
        ("TEST_OSF_A15_20250705131657715_fhir.json",          "osf_main"),
        ("TEST_UPHSM_A04_000000072_fhir.json",                "uphsm_main"),
        ("TEST_UPHSM_A13_20250703090207050_fhir.json",        "uphsm_main"),
        ("TEST_UPHSM_A28_20250702190015050_fhir.json",        "uphsm_main"),
        ("TEST_SCMH_A04_000000215_fhir.json",                 "scmh_main"),
        # ADT facility-based (TEST_adt_*)
        ("TEST_adt_aspirushoughtonclinic_20240903112213_fhir.json",       "aspirus_houghton"),
        ("TEST_adt_aspiruskeweenawlauriumclinic_20240926084226_fhir.json","aspirus_laurium"),
        ("TEST_adt_baragacountymemorialhospital_20240808140200_fhir.json","baraga_main"),
        ("TEST_adt_corewellhealthbutterworthhospital_20240101_fhir.json", "corewell_butterworth"),
        ("TEST_adt_hfjhjacksonhospital_20240101_fhir.json",               "henry_ford_jackson"),
        ("TEST_adt_munisingmemorialhospital_20240101_fhir.json",          "uphsm_munising"),
        ("TEST_adt_munsonhealthcarecharlevoixhospital_20240101_fhir.json","munson_charlevoix"),
        ("TEST_adt_northcarepihp_20240101_fhir.json",                     "northcare"),
        ("TEST_adt_schoolcraftmemorialhospital_20240101_fhir.json",       "scmh_main"),
        ("TEST_adt_uphealthsystem-marquette_20240101_fhir.json",          "uphsm_marquette"),
        ("TEST_adt_uphsportagehealth_20240101_fhir.json",                 "uphsm_portage"),
        # ORU/LAB
        ("TEST_Baraga_LAB_2024-01-01_fhir.json",                       "baraga_main"),
        ("TEST_Marquette_LAB_2024-02-18_fhir.json",                    "uphsm_marquette"),
        ("TEST_HNJH-LAB_2024-01-02-19-42-43-005_fhir.json",           "henry_ford_jackson"),
        # ORU/RAD
        ("TEST_OSF_RAD_2025-07-01-09-45-51-506_fhir.json",            "osf_main"),
        ("TEST_Marquette_RAD_2024-09-26-10-55-42-213_fhir.json",      "uphsm_marquette"),
        ("TEST_Schoolcraft_RAD_2025-01-15-10-00-00-000_fhir.json",    "scmh_main"),
        ("TEST_Aspirus_RAD_2025-03-10-08-30-00-000_fhir.json",        "aspirus_main"),
    ]
    ok = 0
    for fn, expected in tests:
        got = get_hospital_key(fn)
        status = "OK" if got == expected else f"FAIL (expected {expected})"
        print(f"  {status}: {fn[:60]} → {got}")
        if got == expected:
            ok += 1
    print(f"\n{ok}/{len(tests)} tests passed")
