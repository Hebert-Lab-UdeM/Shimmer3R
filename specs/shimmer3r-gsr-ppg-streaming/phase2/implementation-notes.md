# Phase 2 Implementation Notes

**Created:** 2026-07-10
**Last Updated:** 2026-07-10
**Status:** In Development (Stability-First Approach)

---

## Overview

Phase 2 implements Shimmer3R GSR+PPG acquisition in Python, providing equivalent functionality to Phase 1 (MATLAB) while avoiding the Realterm dependency.

**Key Design Principle:** Research-grade reliability over development speed. Data integrity is paramount; crashes or failed recordings are unacceptable.

---

## Implementation Strategy: Hybrid Approach

### Rationale

The pyshimmer library (v1.0.0, PyPI) provides reliable:
- ✅ Device connection via Classic Bluetooth RFCOMM
- ✅ Sensor configuration (enable/disable sensors)
- ✅ Calibration data access (EEPROM queries)
- ✅ Command/response protocol handling

However, pyshimmer has **critical threading issues on Windows**:
- ❌ Background read thread crashes during streaming
- ❌ Thread join() hangs on shutdown
- ❌ Queue race conditions in callback handling

These issues are documented in pyshimmer's source (Master's thesis project, Linux-focused, minimal Windows testing).

### Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Phase 2 Python Stack                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              shimmer3r_gsr_bt.py                      │   │
│  │              (Main Acquisition Script)                │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│         ┌─────────────────┼─────────────────┐               │
│         │                 │                 │               │
│         ▼                 ▼                 ▼               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Connection  │  │   Sensors   │  │   Filter    │         │
│  │  (pyshimmer)│  │ (pyshimmer) │  │  (scipy)    │         │
│  │  ✅ Stable  │  │  ✅ Stable  │  │  ✅ Stable  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│         ┌─────────────────┐        ┌─────────────┐         │
│         │   LSL Output    │        │ CSV Output  │         │
│         │   (pylsl)       │        │ (numpy)     │         │
│         │   ✅ Stable     │        │ ✅ Stable   │         │
│         └─────────────────┘        └─────────────┘         │
│                                                             │
│         ┌─────────────────────────────────────────┐        │
│         │      Data Acquisition (HYBRID)          │        │
│         │                                         │        │
│         │  ┌────────────────┐  ┌──────────────┐  │        │
│         │  │ pyshimmer      │  │ Direct Serial│  │        │
│         │  │ - Config       │  │ - Polling    │  │        │
│         │  │ - Calibration  │  │ - No threads │  │        │
│         │  │ ✅ Reliable    │  │ ✅ Reliable  │  │        │
│         │  └────────────────┘  └──────────────┘  │        │
│         └─────────────────────────────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

| Module | Purpose | Uses pyshimmer? | Stability |
|--------|---------|-----------------|-----------|
| `shimmer_connection.py` | Device connection, initialization | ✅ Yes (connection only) | ✅ Stable |
| `shimmer_sensors.py` | Sensor configuration | ✅ Yes (config only) | ✅ Stable |
| `shimmer_filter.py` | PPG Chebyshev filtering | ❌ No (scipy only) | ✅ Stable |
| `shimmer_lsl.py` | LSL streaming output | ❌ No (pylsl only) | ✅ Stable |
| `shimmer_csv.py` | CSV file output | ❌ No (numpy only) | ✅ Stable |
| `shimmer_serial.py` | **Data polling (NEW)** | ❌ No (direct serial) | ✅ Stable |
| `shimmer3r_gsr_bt.py` | Main acquisition script | ⚠️ Hybrid | ⚠️ Testing |

---

## Development Timeline

### Phase A: Hybrid Implementation (4-6 weeks)

**Week 1-2: Core Implementation**
- [x] Create `shimmer_serial.py` with direct serial I/O
- [ ] Integrate `ShimmerSerialReader` into main acquisition loop
- [ ] Replace `poll_data_chunk()` callback approach with blocking reads
- [ ] Add comprehensive error handling and recovery

**Week 3-4: Calibration Integration**
- [ ] Query calibration data via pyshimmer's `get_all_calibration()`
- [ ] Apply calibration formulas to convert ADC → physical units
- [ ] Verify calibration against Phase 1 MATLAB output
- [ ] Document calibration formulas and sources

**Week 5-6: Validation Testing**
- [ ] Side-by-side comparison with Phase 1 (same signals, both systems)
- [ ] Verify numerical equivalence (within tolerance: ±5% EDA, ±10% PPG)
- [ ] Test edge cases: device disconnect, buffer overflow, long recordings
- [ ] Document any discrepancies

### Phase B: Parallel Deployment (8-12 weeks)

**Week 7-8: Lab Testing**
- [ ] Deploy Phase 2 in parallel with Phase 1 for actual lab sessions
- [ ] Collect feedback from lab members
- [ ] Monitor stability metrics: crash rate, data loss, packet reception
- [ ] Refine based on real-world use

**Week 9-12: Production Readiness**
- [ ] Achieve zero crashes over 20+ lab sessions
- [ ] Document all failure modes and recovery procedures
- [ ] Create troubleshooting guide for lab members
- [ ] Final sign-off from lab coordinator

### Phase C: Long-Term Maintenance (Ongoing)

**Option C1: Fork pyshimmer**
- Create Hebert-Lab-UdeM/pyshimmer fork
- Apply Windows-specific stability fixes
- Pin to specific commit for reproducibility
- Contribute fixes upstream (if responsive)

**Option C2: Reduce Dependencies**
- Implement connection/config ourselves (drop pyshimmer entirely)
- Full control over all components
- Higher maintenance burden

**Decision Point:** After Phase B, based on pyshimmer maintainer responsiveness and lab needs.

---

## Technical Details

### LogAndStream Protocol

**Command Structure:**
```
[Command Byte] [Optional Data] [Checksum]
```

**Key Commands:**
| Command | Byte | Purpose |
|---------|------|---------|
| ACK | `0x00` | Acknowledgment |
| Ping | `0x01` | Connection test |
| Get Device Info | `0x09` | Query hardware/firmware |
| Set Sensors | `0x07` | Enable/disable sensors |
| Start Streaming | `0x05` | Begin data transmission |
| Stop Streaming | `0x06` | End data transmission |

**Data Packet Structure (GSR + PPG):**
```
[0x00] [Timestamp_L] [Timestamp_H] [GSR_L] [GSR_H] [PPG_L] [PPG_H] [...] [Checksum]
```

### Calibration Challenge

**Current Status:** Raw ADC values only

**Required for Production:**
1. Query device EEPROM for calibration data
2. Apply device-specific scaling factors
3. Convert to physical units:
   - EDA: ADC counts → kOhms
   - PPG: ADC counts → mV

**Approach:**
- Use pyshimmer's `get_all_calibration()` method (reliable)
- Apply calibration in post-processing or real-time
- Verify against Phase 1 MATLAB output

**Risk:** Calibration formulas may be embedded in Shimmer's Java JARs. If pyshimmer doesn't expose them properly, we may need to:
- Reverse-engineer from JARs (legally questionable)
- Request documentation from Shimmer Research
- Empirical calibration (record known signals, derive formulas)

### Windows-Specific Issues

**Identified Problems:**
1. **pyshimmer threading:** Background read thread crashes, join() hangs
2. **Serial port access:** Other applications (MATLAB, Consensys) may hold ports
3. **Bluetooth stack:** Windows Bluetooth service may need restart

**Mitigations:**
1. ✅ Direct serial I/O (no pyshimmer threads for data)
2. ⚠️ Documentation and lab procedures (close other apps before use)
3. ⚠️ Troubleshooting guide (restart Bluetooth service if needed)

---

## Testing Protocol

### Pre-Deployment Checklist

Before using Phase 2 for production data:

- [ ] **Unit Tests:** All modules pass individual tests
- [ ] **Integration Test:** Full acquisition completes without crash (10+ sessions)
- [ ] **Calibration Check:** EDA/PPG values match Phase 1 within tolerance
- [ ] **LSL Verification:** Stream visible to LabRecorder, correct metadata
- [ ] **CSV Verification:** Format matches Phase 1, header correct
- [ ] **Error Recovery:** Graceful handling of device disconnect, Ctrl+C
- [ ] **Long Recording:** 30+ minute session without issues
- [ ] **Lab Member Training:** At least 2 lab members trained and comfortable

### Parallel Validation Protocol

During Phase B (parallel deployment):

1. **Record same session with both Phase 1 and Phase 2**
   - Same device, same subject, same time (split signal if possible)
   - Or consecutive sessions with minimal time gap

2. **Compare outputs:**
   - CSV format and header (byte-for-byte match)
   - EDA values (±5% tolerance)
   - PPG values (±10% tolerance, waveform shape match)
   - Packet reception rates (both >80%)

3. **Document discrepancies:**
   - Any systematic differences?
   - Calibration drift?
   - Timing issues?

4. **Sign-off criteria:**
   - 20+ sessions with zero crashes
   - No systematic bias between Phase 1 and Phase 2
   - Lab members comfortable with workflow

---

## File Structure

```
Shimmer3R-2026/python/
├── params_shimmer3r.py          # Acquisition parameters
├── shimmer3r_gsr_bt.py          # Main acquisition script
├── shimmer_connection.py        # Device connection (pyshimmer)
├── shimmer_sensors.py           # Sensor configuration (pyshimmer)
├── shimmer_filter.py            # PPG filtering (scipy)
├── shimmer_lsl.py               # LSL streaming (pylsl)
├── shimmer_csv.py               # CSV output (numpy)
├── shimmer_serial.py            # Direct serial I/O (NEW - hybrid)
├── tests/
│   ├── test_environment.py
│   ├── test_bluetooth_enumeration.py
│   ├── test_pyshimmer_connection.py
│   ├── test_shimmer_ports.py
│   ├── check_shimmer_state.py
│   └── test_simple_serial.py
├── data/                        # Output CSV files
└── requirements.txt             # Python dependencies
```

---

## Dependencies

**Core:**
- Python 3.8+ (tested on 3.11)
- pyshimmer >= 1.0.0 (connection, config, calibration)
- pyserial >= 3.5 (direct serial I/O)
- pylsl >= 1.16.0 (LSL streaming)
- scipy >= 1.11.0 (PPG filtering)
- numpy >= 1.24.0 (numerical operations)

**Development:**
- pytest >= 7.4.0 (testing)

**System:**
- Windows 10/11 with Bluetooth adapter
- Shimmer3R firmware >= 0.15.4 (LogAndStream protocol)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| pyshimmer threading crash | High (confirmed) | High (data loss) | ✅ Hybrid serial approach |
| Calibration mismatch | Medium | High (invalid data) | ⚠️ Parallel validation with Phase 1 |
| Bluetooth interference | Medium | Medium (packet loss) | ⚠️ Lab procedures (proximity, minimize interference) |
| Serial port conflict | Medium | Medium (can't connect) | ⚠️ Lab procedures (close other apps) |
| pyshimmer unmaintained | High (long-term) | Medium (security, bugs) | ⚠️ Fork plan, reduce dependencies |
| Windows Bluetooth stack issues | Low | High (can't connect) | ⚠️ Troubleshooting guide, service restart |

---

## Decision Log

### 2026-07-10: Hybrid Approach Selected

**Decision:** Implement hybrid serial communication instead of fixing pyshimmer upstream or implementing from scratch.

**Rationale:**
1. pyshimmer connection/config/calibration works reliably on Windows
2. Only streaming callbacks are problematic (threading issues)
3. Direct serial I/O avoids threading while keeping pyshimmer benefits
4. Faster than full reimplementation, more reliable than upstream fixes

**Alternatives Considered:**
- Fix pyshimmer upstream: Unlikely to be merged, slow timeline
- Full from-scratch implementation: 4-8 weeks for calibration alone
- Continue with Phase 1 MATLAB only: Limits integration with Python tools

**Sign-off:** Pending lab coordinator approval after parallel validation.

---

## References

- PRD: `specs/shimmer3r-gsr-ppg-streaming/prd.md`
- pyshimmer Source: https://github.com/seemoo-lab/pyshimmer
- Shimmer LogAndStream Protocol: https://github.com/ShimmerResearch/shimmer3-firmware
- Phase 1 MATLAB: `Shimmer3-2022/matlab/StreamShimmer.m`
- Bent & Dunn (2021): PPG sampling rate optimization (64 Hz, 5 Hz LPF)

---

## Next Actions

1. **Integrate `shimmer_serial.py`** into main acquisition loop
2. **Test serial communication** with configured device
3. **Implement calibration** using pyshimmer's `get_all_calibration()`
4. **Begin parallel validation** with Phase 1 MATLAB

**Owner:** S. Devraj
**Timeline:** 4-6 weeks for integration and testing
**Review:** After 10 successful parallel sessions
