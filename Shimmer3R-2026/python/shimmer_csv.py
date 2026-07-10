"""
shimmer_csv.py — CSV file writer for Shimmer3R data.

This module writes Shimmer3R EDA and PPG data to CSV files with a
3-line header format that matches Phase 1 MATLAB implementation exactly.

CSV Format:
    Line 1: Channel names (Timestamp, EDA_kOhms, PPG_mV, PPG_Filtered_mV)
    Line 2: Channel formats (CAL, CAL, CAL, CAL)
    Line 3: Channel units (ms, kOhms, mV, mV)
    Line 4+: Tab-delimited data rows

Usage:
    from shimmer_csv import ShimmerCSVWriter
    
    with ShimmerCSVWriter('./data/', 'subj01') as writer:
        writer.write_row(timestamp_ms, eda, ppg_raw, ppg_filtered)
        writer.write_chunk(timestamps, eda, ppg_raw, ppg_filtered)

Requirements:
    - numpy >= 1.24.0

See also:
    params_shimmer3r.py — Acquisition parameters
"""

import os
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Union
from pathlib import Path

import numpy as np


class ShimmerCSVWriter:
    """
    CSV writer for Shimmer3R EDA and PPG data.
    
    This class writes data to CSV files with a 3-line header format
    that matches Phase 1 MATLAB implementation exactly.
    
    The CSV format is:
        Line 1: Channel names
        Line 2: Channel formats (CAL = calibrated)
        Line 3: Channel units
        Line 4+: Tab-delimited data rows
    
    Attributes:
        filepath: Full path to the CSV file
        n_rows: Number of data rows written (excluding header)
    
    Example:
        >>> writer = ShimmerCSVWriter('./data/', 'subj01')
        >>> writer.write_row(100.0, 1.5, 0.8, 0.75)
        >>> writer.close()
    """
    
    # CSV header format (matches Phase 1 MATLAB)
    HEADER_CHANNEL_NAMES = ['Timestamp', 'EDA_kOhms', 'PPG_mV', 'PPG_Filtered_mV']
    HEADER_CHANNEL_FORMATS = ['CAL', 'CAL', 'CAL', 'CAL']
    HEADER_CHANNEL_UNITS = ['ms', 'kOhms', 'mV', 'mV']
    
    def __init__(
        self,
        output_dir: str = './data/',
        subject_id: str = 'subj01',
        timestamp: Optional[datetime] = None,
        precision: int = 16,
        delimiter: str = '\t',
        verbose: bool = True,
    ):
        """
        Initialize CSV writer and create output file.
        
        Args:
            output_dir: Directory for CSV output (created if needed)
            subject_id: Subject identifier for filename
            timestamp: Session timestamp (default: current UTC time)
            precision: Floating point precision (digits, default: 16)
            delimiter: Column delimiter (default: tab)
            verbose: Print progress messages (default: True)
        
        Raises:
            OSError: If output directory cannot be created
        """
        
        self.output_dir = Path(output_dir)
        self.subject_id = subject_id
        self.precision = precision
        self.delimiter = delimiter
        self.verbose = verbose
        
        # Create output directory if needed
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename: {subject_id}_{ISO-8601 timestamp}.csv
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # ISO-8601 format: yyyy-MM-dd'T'HH-mm-ss
        timestamp_str = timestamp.strftime('%Y-%m-%dT%H-%M-%S')
        self.filename = f'{subject_id}_{timestamp_str}.csv'
        self.filepath = self.output_dir / self.filename
        
        # Open file and write header
        self._file_handle = None
        self.n_rows = 0
        self._open_and_write_header()
        
        if verbose:
            print(f"[CSV] Output file: {self.filepath}")
    
    def _open_and_write_header(self) -> None:
        """Open file and write 3-line header."""
        
        # Open file in text mode with UTF-8 encoding
        self._file_handle = open(self.filepath, 'w', encoding='utf-8', newline='')
        
        # Write 3-line header
        # Line 1: Channel names
        header_names = self.delimiter.join(self.HEADER_CHANNEL_NAMES)
        self._file_handle.write(header_names + '\n')
        
        # Line 2: Channel formats
        header_formats = self.delimiter.join(self.HEADER_CHANNEL_FORMATS)
        self._file_handle.write(header_formats + '\n')
        
        # Line 3: Channel units
        header_units = self.delimiter.join(self.HEADER_CHANNEL_UNITS)
        self._file_handle.write(header_units + '\n')
        
        if self.verbose:
            print(f"[CSV] Header written (3 lines)")
            print(f"      Columns: {', '.join(self.HEADER_CHANNEL_NAMES)}")
    
    def write_row(
        self,
        timestamp_ms: float,
        eda_kohms: float,
        ppg_mV: float,
        ppg_filtered_mV: float,
    ) -> None:
        """
        Write a single data row to CSV.
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            eda_kohms: EDA/GSR value in kOhms
            ppg_mV: Raw PPG value in mV
            ppg_filtered_mV: Filtered PPG value in mV
        """
        
        if self._file_handle is None:
            raise RuntimeError("CSV writer is closed")
        
        # Format with specified precision
        row = (
            f"{timestamp_ms:.{self.precision}f}"
            f"{self.delimiter}{eda_kohms:.{self.precision}f}"
            f"{self.delimiter}{ppg_mV:.{self.precision}f}"
            f"{self.delimiter}{ppg_filtered_mV:.{self.precision}f}"
            f"\n"
        )
        
        self._file_handle.write(row)
        self.n_rows += 1
    
    def write_chunk(
        self,
        timestamps: np.ndarray,
        eda: np.ndarray,
        ppg_raw: np.ndarray,
        ppg_filtered: np.ndarray,
    ) -> int:
        """
        Write a chunk of data rows to CSV.
        
        This method is more efficient than write_row() for multiple samples.
        
        Args:
            timestamps: Timestamp array (nSamples,) in ms
            eda: EDA array (nSamples,) in kOhms
            ppg_raw: Raw PPG array (nSamples,) in mV
            ppg_filtered: Filtered PPG array (nSamples,) in mV
        
        Returns:
            Number of rows written
        """
        
        if self._file_handle is None:
            raise RuntimeError("CSV writer is closed")
        
        # Validate input
        n_samples = len(timestamps)
        if not all(len(arr) == n_samples for arr in [eda, ppg_raw, ppg_filtered]):
            raise ValueError("All input arrays must have same length")
        
        if n_samples == 0:
            return 0
        
        # Stack data into [nSamples × 4] array
        data = np.column_stack([timestamps, eda, ppg_raw, ppg_filtered])
        
        # Format and write
        # Use numpy's savetxt for efficiency
        fmt = f"%.{self.precision}f"
        
        # Write to file handle
        np.savetxt(
            self._file_handle,
            data,
            fmt=fmt,
            delimiter=self.delimiter,
        )
        
        self.n_rows += n_samples
        
        if self.verbose:
            print(f"[CSV] Wrote {n_samples} rows (total: {self.n_rows})")
        
        return n_samples
    
    def flush(self) -> None:
        """
        Flush buffer to disk.
        
        Call this periodically during long recordings to prevent
        data loss on crash.
        """
        
        if self._file_handle:
            self._file_handle.flush()
            os.fsync(self._file_handle.fileno())
    
    def close(self) -> None:
        """
        Close CSV file and finalize.
        
        This should be called when finished writing to ensure all
        data is flushed to disk.
        """
        
        if self._file_handle:
            self.flush()
            self._file_handle.close()
            self._file_handle = None
            
            if self.verbose:
                print(f"[CSV] File closed: {self.n_rows} data rows")
                print(f"      Path: {self.filepath}")
    
    def get_file_size(self) -> int:
        """
        Get current file size in bytes.
        
        Returns:
            File size in bytes, or 0 if file not accessible
        """
        
        try:
            return self.filepath.stat().st_size
        except OSError:
            return 0
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure file is closed."""
        self.close()
        return False  # Don't suppress exceptions


def create_csv_filename(
    subject_id: str = 'subj01',
    timestamp: Optional[datetime] = None,
    output_dir: str = './data/',
) -> Path:
    """
    Create CSV filename with ISO-8601 timestamp.
    
    This is a convenience function for generating filenames that
    match the Phase 1 MATLAB naming convention.
    
    Args:
        subject_id: Subject identifier
        timestamp: Session timestamp (default: current UTC time)
        output_dir: Output directory
    
    Returns:
        Path object with full filepath
    """
    
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    timestamp_str = timestamp.strftime('%Y-%m-%dT%H-%M-%S')
    filename = f'{subject_id}_{timestamp_str}.csv'
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    return output_path / filename


def write_csv_header(
    filepath: Union[str, Path],
    delimiter: str = '\t',
) -> None:
    """
    Write CSV header to file.
    
    This is a low-level function for writing just the header.
    Use ShimmerCSVWriter for complete functionality.
    
    Args:
        filepath: Output file path
        delimiter: Column delimiter (default: tab)
    """
    
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    header_names = delimiter.join(['Timestamp', 'EDA_kOhms', 'PPG_mV', 'PPG_Filtered_mV'])
    header_formats = delimiter.join(['CAL', 'CAL', 'CAL', 'CAL'])
    header_units = delimiter.join(['ms', 'kOhms', 'mV', 'mV'])
    
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        f.write(header_names + '\n')
        f.write(header_formats + '\n')
        f.write(header_units + '\n')


def verify_csv_format(
    filepath: Union[str, Path],
    expected_columns: int = 4,
    expected_header_lines: int = 3,
) -> dict:
    """
    Verify CSV file format matches Phase 1 specification.
    
    This function checks that the CSV file has the correct header
    format and data structure.
    
    Args:
        filepath: Path to CSV file
        expected_columns: Expected number of data columns (default: 4)
        expected_header_lines: Expected header lines (default: 3)
    
    Returns:
        Dict with verification results:
        - valid: bool (True if format matches spec)
        - header_names: list of channel names
        - header_formats: list of formats
        - header_units: list of units
        - n_data_rows: number of data rows
        - n_columns: number of data columns
        - errors: list of error messages
    """
    
    filepath = Path(filepath)
    
    results = {
        'valid': True,
        'header_names': [],
        'header_formats': [],
        'header_units': [],
        'n_data_rows': 0,
        'n_columns': 0,
        'errors': [],
    }
    
    if not filepath.exists():
        results['valid'] = False
        results['errors'].append(f"File not found: {filepath}")
        return results
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) < expected_header_lines + 1:
            results['valid'] = False
            results['errors'].append(
                f"File too short: {len(lines)} lines "
                f"(expected >= {expected_header_lines + 1})"
            )
            return results
        
        # Parse header lines
        delimiter = '\t' if '\t' in lines[0] else ','
        
        results['header_names'] = lines[0].strip().split(delimiter)
        results['header_formats'] = lines[1].strip().split(delimiter)
        results['header_units'] = lines[2].strip().split(delimiter)
        
        # Verify header content
        expected_names = ['Timestamp', 'EDA_kOhms', 'PPG_mV', 'PPG_Filtered_mV']
        expected_formats = ['CAL', 'CAL', 'CAL', 'CAL']
        expected_units = ['ms', 'kOhms', 'mV', 'mV']
        
        if results['header_names'] != expected_names:
            results['valid'] = False
            results['errors'].append(
                f"Header names mismatch: {results['header_names']} "
                f"!= {expected_names}"
            )
        
        if results['header_formats'] != expected_formats:
            results['valid'] = False
            results['errors'].append(
                f"Header formats mismatch: {results['header_formats']} "
                f"!= {expected_formats}"
            )
        
        if results['header_units'] != expected_units:
            results['valid'] = False
            results['errors'].append(
                f"Header units mismatch: {results['header_units']} "
                f"!= {expected_units}"
            )
        
        # Count data rows and columns
        data_lines = lines[expected_header_lines:]
        results['n_data_rows'] = len(data_lines)
        
        if data_lines:
            results['n_columns'] = len(data_lines[0].strip().split(delimiter))
            
            if results['n_columns'] != expected_columns:
                results['valid'] = False
                results['errors'].append(
                    f"Column count mismatch: {results['n_columns']} "
                    f"!= {expected_columns}"
                )
        
    except Exception as e:
        results['valid'] = False
        results['errors'].append(f"Error reading file: {e}")
    
    return results


# =============================================================================
# Command-Line Interface
# =============================================================================

if __name__ == '__main__':
    """Test CSV writer functionality."""
    import argparse
    import time
    import sys
    
    parser = argparse.ArgumentParser(
        description='Test Shimmer3R CSV writer'
    )
    parser.add_argument(
        '--subject',
        type=str,
        default='test_subj',
        help='Subject ID for filename (default: test_subj)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./data/',
        help='Output directory (default: ./data/)'
    )
    parser.add_argument(
        '--duration',
        type=float,
        default=2.0,
        help='Test duration in seconds (default: 2)'
    )
    parser.add_argument(
        '--rate',
        type=float,
        default=64.0,
        help='Simulated sampling rate in Hz (default: 64)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify output file format after writing'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("CSV Writer Test")
    print("="*70 + "\n")
    
    try:
        # Create writer
        with ShimmerCSVWriter(
            output_dir=args.output_dir,
            subject_id=args.subject,
            verbose=not args.quiet,
        ) as writer:
            
            print(f"\nWriting test data for {args.duration}s at {args.rate} Hz...")
            
            # Generate synthetic data
            n_samples = int(args.rate * args.duration)
            t_ms = np.linspace(0, args.duration * 1000, n_samples)
            
            # Simulate EDA (slow drift + noise)
            eda = 2.0 + 0.5 * np.sin(2 * np.pi * 0.1 * t_ms / 1000) + 0.1 * np.random.randn(n_samples)
            
            # Simulate PPG (pulse waveform)
            heart_rate_hz = 1.2
            ppg_raw = (
                1.0 * np.sin(2 * np.pi * heart_rate_hz * t_ms / 1000) +
                0.3 * np.sin(2 * np.pi * 2 * heart_rate_hz * t_ms / 1000) +
                0.2 * np.random.randn(n_samples)
            )
            
            # Simulate filtered PPG (smoothed)
            from scipy.ndimage import gaussian_filter1d
            ppg_filtered = gaussian_filter1d(ppg_raw, sigma=2)
            
            # Write data in chunks
            chunk_size = 32
            n_chunks = n_samples // chunk_size
            
            start_time = time.time()
            for i in range(n_chunks):
                start_idx = i * chunk_size
                end_idx = start_idx + chunk_size
                
                writer.write_chunk(
                    t_ms[start_idx:end_idx],
                    eda[start_idx:end_idx],
                    ppg_raw[start_idx:end_idx],
                    ppg_filtered[start_idx:end_idx],
                )
                
                # Simulate real-time writing
                time.sleep(chunk_size / args.rate)
            
            elapsed = time.time() - start_time
            
            print(f"\n✓ Wrote {writer.n_rows} data rows in {elapsed:.1f}s")
            print(f"  File size: {writer.get_file_size() / 1024:.1f} KB")
            print(f"  File: {writer.filepath}")
        
        # Verify output
        if args.verify:
            print(f"\nVerifying CSV format...")
            results = verify_csv_format(writer.filepath)
            
            if results['valid']:
                print(f"✓ CSV format is valid")
                print(f"  Header names: {results['header_names']}")
                print(f"  Header formats: {results['header_formats']}")
                print(f"  Header units: {results['header_units']}")
                print(f"  Data rows: {results['n_data_rows']}")
                print(f"  Columns: {results['n_columns']}")
            else:
                print(f"✗ CSV format validation failed:")
                for error in results['errors']:
                    print(f"  - {error}")
        
        print(f"\n✓ CSV writer test PASSED")
        
    except Exception as e:
        print(f"\n✗ CSV writer test FAILED")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "="*70 + "\n")
