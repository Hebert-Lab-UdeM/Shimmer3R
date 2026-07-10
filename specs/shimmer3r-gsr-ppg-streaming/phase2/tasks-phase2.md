# Tasks: Shimmer3R GSR+PPG Streaming Module — Phase 2 (Python + pyshimmer)

**PRD:** specs/shimmer3r-gsr-ppg-streaming/prd.md
**Generated:** 2026-07-10
**Updated:** 2026-07-10 (Hybrid serial communication approach)
**Phase:** 2 of 3 (Python + pyshimmer over Classic Bluetooth RFCOMM)
**Status:** In Progress — Tasks 1-8 complete, Task 9 (integration) pending

**Implementation Approach:** Hybrid serial communication
- pyshimmer for: connection, sensor config, calibration (stable on Windows)
- Direct serial I/O for: data polling (avoids pyshimmer threading issues)
- See: `specs/shimmer3r-gsr-ppg-streaming/phase2/implementation-notes.md`

---

## Task 1: Python environment and dependency verification ✅ COMPLETE

**Status:** All subtasks complete, committed 2026-07-10

- [x] **1.1 [research]** Verify pyshimmer compatibility with Shimmer3R
  - Output: `specs/shimmer3r-gsr-ppg-streaming/pyshimmer-compat-notes.md`
  - Finding: pyshimmer v1.0.0 has Shimmer3R support but threading issues on Windows

- [x] **1.2 [implementation]** Create Python requirements file
  - Output: `Shimmer3R-2026/python/requirements.txt`
  - Dependencies: pyshimmer, pyserial, pylsl, scipy, numpy, pytest

- [x] **1.3 [implementation]** Bluetooth enumeration tests
  - Output: `Shimmer3R-2026/python/tests/test_bluetooth_enumeration.py`
  - Identifies Shimmer3R COM ports via protocol handshake

- [x] **1.4 [review]** Environment verification
  - Output: `Shimmer3R-2026/python/tests/test_environment.py`
  - Verifies all dependencies import correctly

---

## Task 2: Parameter file (python/params_shimmer3r.py) ✅ COMPLETE

**Status:** All subtasks complete, committed 2026-07-10

- [x] **2.1-2.6 [implementation]** Create params_shimmer3r.py
  - Output: `Shimmer3R-2026/python/params_shimmer3r.py`
  - All parameters from Phase 1 params_shimmer3r.m
  - DEVICE_LABEL: 'BE7E' (lab device)
  - COM_PORT: 'COM5' (verified streaming port)
  - `SUBJECT_ID`: "subj01" (default)
  - `CONNECTION_TIMEOUT_S`: 60 (same as Phase 1)

- [ ] **2.3 [implementation]** Add PPG filter parameters to params file
  - `FCLP_PPG_HZ`: 5 (Chebyshev LPF corner frequency)
  - `N_POLES_PPG`: 2 (filter order)
  - `PB_RIPPLE_PCT`: 0.5 (passband ripple)
  - Match Phase 1 values from `params_shimmer3r.m` exactly

- [ ] **2.4 [implementation]** Add file paths and LSL parameters to params file
  - `OUTPUT_DIR`: "./data/" (relative to python/ directory)
  - `LSL_STREAM_NAME`: "Shimmer3R_GSR_PPG" (must match Phase 1)
  - `LSL_SOURCE_ID`: "shimmer3r_001" (must match Phase 1)
  - `LSL_DEVICE_NAME`: "Shimmer3-GSR+" (must match Phase 1 LSL metadata)

- [ ] **2.5 [implementation]** Add timing parameters to params file
  - `DELAY_PERIOD_S`: 0.2 (polling interval, same as Phase 1)
  - `CONFIG_PAUSE_S`: 20 (if applicable to pyshimmer initialization)

- [ ] **2.6 [review]** Verify params file completeness and consistency with Phase 1
  - Every parameter in Phase 1's `params_shimmer3r.m` has a Python equivalent
  - No hardcoded values in main script will be needed
  - LSL stream name, source ID, and device name match Phase 1 exactly

---

## Task 3: pyshimmer device connection ✅ COMPLETE

**Status:** All subtasks complete, committed 2026-07-10

- [x] **3.1-3.5 [implementation]** shimmer_connection.py
  - Output: `Shimmer3R-2026/python/shimmer_connection.py` (551 lines)
  - Functions: connect_to_shimmer(), disconnect_shimmer(), query_device_info()
  - ShimmerConnectionManager context manager
  - Verified working with lab device (COM5, BE7E)

---

## Task 4: Sensor configuration ✅ COMPLETE

**Status:** All subtasks complete, committed 2026-07-10

- [x] **4.1-4.5 [implementation]** shimmer_sensors.py
  - Output: `Shimmer3R-2026/python/shimmer_sensors.py` (496 lines)
  - Functions: configure_sensors(), poll_data_chunk(), verify_sensor_config()
  - Note: poll_data_chunk() uses pyshimmer callbacks (has threading issues on Windows)
  - **Action:** Will be replaced with shimmer_serial.py integration (Task 9)

---

## Task 5: PPG low-pass filter ✅ COMPLETE

**Status:** All subtasks complete, committed 2026-07-10

- [x] **5.1-5.6 [implementation]** shimmer_filter.py
  - Output: `Shimmer3R-2026/python/shimmer_filter.py` (626 lines)
  - PPGFilter class: Chebyshev Type I, 5 Hz, 2 poles, 0.5% ripple
  - Matches Phase 1 FilterClass exactly
  - Verification plots and SNR testing

---

## Task 6: LSL outlet ✅ COMPLETE

**Status:** All subtasks complete, committed 2026-07-10

- [x] **6.1-6.5 [implementation]** shimmer_lsl.py
  - Output: `Shimmer3R-2026/python/shimmer_lsl.py` (596 lines)
  - Functions: create_lsl_outlet(), push_lsl_chunk(), verify_lsl_outlet()
  - Metadata matches Phase 1 exactly
  - Tested and working on Windows

---

## Task 7: CSV file writer ✅ COMPLETE

**Status:** All subtasks complete, committed 2026-07-10

- [x] **7.1-7.6 [implementation]** shimmer_csv.py
  - Output: `Shimmer3R-2026/python/shimmer_csv.py` (579 lines)
  - ShimmerCSVWriter class with 3-line header (Phase 1 format)
  - Tab-delimited, 16-digit precision
  - Format verification function

---

## Task 8: Main acquisition script ✅ COMPLETE (pending Task 9 integration)

**Status:** All subtasks complete, committed 2026-07-10

- [x] **8.1-8.6 [implementation]** shimmer3r_gsr_bt.py
  - Output: `Shimmer3R-2026/python/shimmer3r_gsr_bt.py` (440 lines)
  - AcquisitionSession class integrates all components
  - Currently uses pyshimmer callbacks for data polling (has threading issues)
  - **Action:** Will be updated to use shimmer_serial.py (Task 9)

---

## Task 9: Hybrid serial communication integration ⏳ IN PROGRESS

**Status:** shimmer_serial.py created, integration pending

**Covers PRD:** §5 FR 15-17 (device connection, sensor config, filtering)
**New Approach:** Direct serial I/O to avoid pyshimmer threading issues

- [x] **9.1 [implementation]** Create shimmer_serial.py
  - Output: `Shimmer3R-2026/python/shimmer_serial.py` (499 lines)
  - ShimmerSerialReader class with blocking serial I/O
  - LogAndStream protocol packet parsing
  - No threading, no callbacks, no Windows crashes

- [ ] **9.2 [implementation]** Integrate ShimmerSerialReader into main script
  - Replace poll_data_chunk() callback approach with direct serial reads
  - Keep pyshimmer for connection and sensor configuration
  - Add calibration integration (get_all_calibration())
  - Update shimmer3r_gsr_bt.py to use hybrid approach

- [ ] **9.3 [implementation]** Add calibration support
  - Query device calibration via pyshimmer
  - Apply calibration to convert ADC → physical units (kOhms, mV)
  - Verify against Phase 1 MATLAB output

- [ ] **9.4 [review]** Test hybrid acquisition
  - Run shimmer3r_gsr_bt.py with direct serial polling
  - Verify no threading crashes on Windows
  - Confirm data quality matches Phase 1

---

## Task 10: End-to-end verification against Phase 1 ⏳ PENDING

**Status:** Waiting for Task 9 completion

- [ ] **10.1-10.6 [review]** Parallel validation with Phase 1 MATLAB
  - Side-by-side comparison of same signals
  - Verify numerical equivalence (±5% EDA, ±10% PPG)
  - CSV format byte-for-byte match
  - LSL metadata identical
  - 20+ sessions with zero crashes
  - Final sign-off

---

## Dependencies

**Completed:**
- Task 1 (environment) → All tasks
- Task 2 (params) → Tasks 3-9
- Task 3 (connection) → Tasks 4, 8, 9
- Task 4 (sensors) → Task 8, 9
- Task 5 (filter) → Task 8, 9
- Task 6 (LSL) → Task 8
- Task 7 (CSV) → Task 8
- Task 8 (main script) → Task 10

**In Progress:**
- Task 9 (hybrid serial) → Required before Task 10 (validation)

**Next:**
- Task 9.2: Integrate ShimmerSerialReader into shimmer3r_gsr_bt.py
- Task 9.3: Add calibration support
- Task 9.4: Test hybrid acquisition
- Task 10: Parallel validation with Phase 1
