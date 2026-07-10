"""
shimmer_filter.py — PPG signal filtering for Shimmer3R.

This module provides a Chebyshev Type I low-pass filter for PPG signal
processing, matching the Phase 1 MATLAB FilterClass implementation.

Usage:
    from shimmer_filter import create_ppg_filter, filter_ppg_chunk
    
    # Create filter (5 Hz, 2 poles, 0.5% ripple, 64 Hz sampling)
    ppg_filter = create_ppg_filter(sampling_rate_hz=64)
    
    # Filter data chunk
    ppg_filtered = filter_ppg_chunk(ppg_raw, ppg_filter)

Requirements:
    - scipy >= 1.11.0
    - numpy >= 1.24.0

Reference:
    - Bent, B. & Dunn, J.P. (2021). Optimizing sampling rate of wrist-worn
      optical sensors for physiologic monitoring. Journal of Clinical and
      Translational Science, 5, e34, 1–8. doi: 10.1017/cts.2020.526
    - Smith, S.W. (1997). The Scientist and Engineer's Guide to Digital
      Signal Processing, Ch. 20 (Chebyshev Filters).
"""

from typing import Optional, List, Union
from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy.signal import cheby1, lfilter, lfiltic


class FilterType(Enum):
    """Filter type enumeration."""
    LPF = "Low-Pass"
    HPF = "High-Pass"
    BSF = "Band-Stop"


@dataclass
class FilterConfig:
    """Container for filter configuration."""
    
    #: Filter type (LPF, HPF, BSF)
    filter_type: FilterType
    
    #: Sampling rate in Hz
    sampling_rate_hz: float
    
    #: Corner/cutoff frequency in Hz (or [low, high] for band-stop)
    corner_freq_hz: Union[float, List[float]]
    
    #: Filter order (number of poles, must be even for Chebyshev)
    order: int
    
    #: Passband ripple in percent
    ripple_pct: float
    
    def __str__(self) -> str:
        """Return human-readable config summary."""
        if isinstance(self.corner_freq_hz, list):
            freq_str = f"[{self.corner_freq_hz[0]}, {self.corner_freq_hz[1]}] Hz"
        else:
            freq_str = f"{self.corner_freq_hz} Hz"
        
        return (
            f"Filter Configuration:\n"
            f"  Type: {self.filter_type.value}\n"
            f"  Corner Frequency: {freq_str}\n"
            f"  Order: {self.order} poles\n"
            f"  Passband Ripple: {self.ripple_pct}%\n"
            f"  Sampling Rate: {self.sampling_rate_hz} Hz"
        )


class PPGFilter:
    """
    Chebyshev Type I low-pass filter for PPG signal processing.
    
    This class implements a stateful filter that maintains internal state
    across calls, enabling continuous online filtering of streamed data
    chunks without edge artifacts between iterations.
    
    The filter design matches the Phase 1 MATLAB FilterClass implementation:
    - Chebyshev Type I IIR filter
    - Configurable corner frequency, order, and passband ripple
    - State buffer maintained across filter calls
    
    Attributes:
        config: FilterConfig object with filter parameters
        b: Numerator coefficients of filter transfer function
        a: Denominator coefficients of filter transfer function
        zi: Initial filter state (maintained across calls)
    
    Example:
        >>> filter = PPGFilter(sampling_rate_hz=64, corner_freq_hz=5.0,
        ...                    order=2, ripple_pct=0.5)
        >>> filtered = filter.filter(ppg_raw_chunk)
    """
    
    def __init__(
        self,
        sampling_rate_hz: float,
        corner_freq_hz: float = 5.0,
        order: int = 2,
        ripple_pct: float = 0.5,
    ):
        """
        Initialize PPG low-pass filter.
        
        Args:
            sampling_rate_hz: Sampling rate in Hz
            corner_freq_hz: Low-pass corner frequency in Hz (default: 5.0)
            order: Filter order/number of poles (default: 2, must be even)
            ripple_pct: Passband ripple in percent (default: 0.5)
        
        Raises:
            ValueError: If order is not even or frequencies are invalid
        """
        
        # Validate parameters
        if order % 2 != 0:
            raise ValueError(f"Filter order must be even, got {order}")
        
        if corner_freq_hz <= 0:
            raise ValueError(f"Corner frequency must be positive, got {corner_freq_hz}")
        
        if corner_freq_hz >= sampling_rate_hz / 2:
            raise ValueError(
                f"Corner frequency ({corner_freq_hz} Hz) must be less than "
                f"Nyquist frequency ({sampling_rate_hz / 2} Hz)"
            )
        
        if ripple_pct <= 0 or ripple_pct >= 100:
            raise ValueError(f"Ripple must be 0-100%, got {ripple_pct}%")
        
        # Store configuration
        self.config = FilterConfig(
            filter_type=FilterType.LPF,
            sampling_rate_hz=sampling_rate_hz,
            corner_freq_hz=corner_freq_hz,
            order=order,
            ripple_pct=ripple_pct,
        )
        
        # Design filter
        self.b, self.a = self._design_filter()
        
        # Initialize filter state
        # For an Nth order filter, we need N state values per coefficient
        # zi shape: (max(len(a), len(b)) - 1,) for 1D filtering
        self.zi = np.zeros(max(len(self.a), len(self.b)) - 1)
    
    def _design_filter(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Design Chebyshev Type I low-pass filter.
        
        Returns:
            Tuple of (b, a) numerator and denominator coefficients
        """
        # Normalize corner frequency to Nyquist (0 to 1, where 1 = Nyquist)
        nyquist = self.config.sampling_rate_hz / 2
        Wn = self.config.corner_freq_hz / nyquist
        
        # Convert ripple from percent to dB
        # Chebyshev ripple parameter: ripple in passband in dB
        # 0.5% ripple ≈ 0.0436 dB
        ripple_db = -20 * np.log10(1 - self.config.ripple_pct / 100)
        
        # Design Chebyshev Type I filter
        # cheby1 returns (b, a) coefficients for IIR filter
        b, a = cheby1(
            N=self.config.order,          # Filter order
            rp=ripple_db,                 # Passband ripple in dB
            Wn=Wn,                        # Normalized corner frequency
            btype='low',                  # Low-pass filter
            analog=False,                 # Digital filter
            output='ba',                  # Return numerator/denominator coefficients
        )
        
        return b, a
    
    def filter(self, data: np.ndarray) -> np.ndarray:
        """
        Filter a chunk of data, maintaining state across calls.
        
        This method applies the filter to the input data and maintains
        the filter state for continuous filtering of subsequent chunks.
        
        Args:
            data: Input data array (1D)
        
        Returns:
            Filtered data array (same shape as input)
        
        Example:
            >>> filter = PPGFilter(64, 5.0, 2, 0.5)
            >>> chunk1 = np.array([...])  # First data chunk
            >>> filtered1 = filter.filter(chunk1)
            >>> chunk2 = np.array([...])  # Second data chunk
            >>> filtered2 = filter.filter(chunk2)  # Continues smoothly
        """
        
        data = np.asarray(data, dtype=np.float64)
        
        if data.ndim != 1:
            raise ValueError(f"Input data must be 1D, got shape {data.shape}")
        
        # Apply filter with state
        # lfilter applies IIR filter
        # lfiltic sets initial conditions from state vector
        filtered, self.zi = lfilter(
            self.b,
            self.a,
            data,
            zi=self.zi,
        )
        
        return filtered
    
    def filter_sample(self, sample: float) -> float:
        """
        Filter a single sample (for online/streaming use).
        
        This method filters one sample at a time, maintaining state
        for continuous filtering. Less efficient than filter() for
        chunks, but useful for real-time streaming.
        
        Args:
            sample: Single input sample value
        
        Returns:
            Filtered sample value
        """
        
        # Wrap single sample in array
        data = np.array([sample], dtype=np.float64)
        
        # Filter
        filtered, self.zi = lfilter(self.b, self.a, data, zi=self.zi)
        
        return float(filtered[0])
    
    def reset_state(self) -> None:
        """
        Reset filter state to zero.
        
        Call this when starting a new recording session or when
        discontinuity in the signal is expected.
        """
        self.zi = np.zeros_like(self.zi)
    
    def get_frequency_response(
        self,
        n_points: int = 512
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Get filter frequency response for visualization.
        
        Args:
            n_points: Number of frequency points (default: 512)
        
        Returns:
            Tuple of (frequencies_hz, magnitude_db)
        """
        from scipy.signal import freqz
        
        # Compute frequency response
        w, h = freqz(self.b, self.a, worN=n_points)
        
        # Convert to Hz and dB
        frequencies_hz = w * self.config.sampling_rate_hz / (2 * np.pi)
        magnitude_db = 20 * np.log10(np.abs(h))
        
        return frequencies_hz, magnitude_db


def create_ppg_filter(
    sampling_rate_hz: float = 64,
    corner_freq_hz: float = 5.0,
    order: int = 2,
    ripple_pct: float = 0.5,
) -> PPGFilter:
    """
    Create a PPG low-pass filter with standard parameters.
    
    This is a convenience function that creates a PPGFilter with
    parameters matching Phase 1 MATLAB FilterClass.
    
    Args:
        sampling_rate_hz: Sampling rate in Hz (default: 64)
        corner_freq_hz: Corner frequency in Hz (default: 5.0)
        order: Filter order (default: 2)
        ripple_pct: Passband ripple % (default: 0.5)
    
    Returns:
        PPGFilter instance
    
    Example:
        >>> ppg_filter = create_ppg_filter(sampling_rate_hz=64)
        >>> filtered = ppg_filter.filter(ppg_raw)
    """
    
    return PPGFilter(
        sampling_rate_hz=sampling_rate_hz,
        corner_freq_hz=corner_freq_hz,
        order=order,
        ripple_pct=ripple_pct,
    )


def filter_ppg_chunk(
    ppg_raw: np.ndarray,
    ppg_filter: PPGFilter,
) -> np.ndarray:
    """
    Filter a chunk of PPG data.
    
    This is a convenience function that applies the filter to a chunk
    of PPG data.
    
    Args:
        ppg_raw: Raw PPG data array (1D)
        ppg_filter: PPGFilter instance
    
    Returns:
        Filtered PPG data array (same shape as input)
    """
    
    return ppg_filter.filter(ppg_raw)


def filter_ppg_sample(
    ppg_sample: float,
    ppg_filter: PPGFilter,
) -> float:
    """
    Filter a single PPG sample.
    
    This is a convenience function for filtering one sample at a time
    in streaming applications.
    
    Args:
        ppg_sample: Raw PPG sample value
        ppg_filter: PPGFilter instance
    
    Returns:
        Filtered PPG sample value
    """
    
    return ppg_filter.filter_sample(ppg_sample)


def verify_filter(
    ppg_filter: PPGFilter,
    sampling_rate_hz: float = 64,
    plot_path: Optional[str] = None,
) -> dict:
    """
    Verify filter characteristics and optionally plot frequency response.
    
    This function computes filter metrics and can generate a verification
    plot showing the frequency response.
    
    Args:
        ppg_filter: PPGFilter instance to verify
        sampling_rate_hz: Sampling rate for plot (default: 64)
        plot_path: Path to save verification plot (default: None = no plot)
    
    Returns:
        Dict with filter metrics:
        - corner_freq_hz: Actual -3dB corner frequency
        - attenuation_at_10hz: Attenuation at 10 Hz in dB
        - attenuation_at_20hz: Attenuation at 20 Hz in dB
        - passband_ripple_db: Actual passband ripple in dB
    """
    
    # Get frequency response
    frequencies, magnitude_db = ppg_filter.get_frequency_response()
    
    # Find -3dB point (corner frequency)
    corner_idx = np.where(magnitude_db <= -3)[0]
    if len(corner_idx) > 0:
        corner_freq_actual = frequencies[corner_idx[0]]
    else:
        corner_freq_actual = float('inf')
    
    # Get attenuation at specific frequencies
    def get_attenuation(freq_hz: float) -> float:
        idx = np.argmin(np.abs(frequencies - freq_hz))
        return -magnitude_db[idx]  # Negative because magnitude_db is already negative
    
    attenuation_10hz = get_attenuation(10.0)
    attenuation_20hz = get_attenuation(20.0)
    
    # Get passband ripple (max variation in passband)
    passband_mask = frequencies <= ppg_filter.config.corner_freq_hz
    passband_response = magnitude_db[passband_mask]
    passband_ripple = np.max(passband_response) - np.min(passband_response)
    
    metrics = {
        'corner_freq_hz': corner_freq_actual,
        'attenuation_at_10hz': attenuation_10hz,
        'attenuation_at_20hz': attenuation_20hz,
        'passband_ripple_db': passband_ripple,
    }
    
    # Generate plot if requested
    if plot_path:
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        # Plot frequency response
        ax.plot(frequencies, magnitude_db, 'b-', linewidth=2, label='Frequency Response')
        
        # Mark corner frequency
        ax.axvline(ppg_filter.config.corner_freq_hz, color='r', linestyle='--',
                   label=f"Corner Frequency ({ppg_filter.config.corner_freq_hz} Hz)")
        
        # Mark -3dB line
        ax.axhline(-3, color='g', linestyle=':', label='-3 dB')
        
        # Mark Nyquist
        nyquist = sampling_rate_hz / 2
        ax.axvline(nyquist, color='k', linestyle=':', alpha=0.5, label=f'Nyquist ({nyquist} Hz)')
        
        # Formatting
        ax.set_xlabel('Frequency (Hz)', fontsize=12)
        ax.set_ylabel('Magnitude (dB)', fontsize=12)
        ax.set_title(f'PPG Filter Frequency Response\n'
                     f'{ppg_filter.config.filter_type.value}, '
                     f'{ppg_filter.config.order} poles, '
                     f'{ppg_filter.config.corner_freq_hz} Hz corner',
                     fontsize=14)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, nyquist])
        ax.set_ylim([-80, 5])
        
        # Add metrics text box
        textstr = (
            f"Metrics:\n"
            f"Corner (-3dB): {corner_freq_actual:.2f} Hz\n"
            f"@ 10 Hz: {attenuation_10hz:.1f} dB\n"
            f"@ 20 Hz: {attenuation_20hz:.1f} dB\n"
            f"Passband ripple: {passband_ripple:.3f} dB"
        )
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.savefig(plot_path, dpi=150)
        plt.close()
    
    return metrics


# =============================================================================
# Command-Line Interface
# =============================================================================

if __name__ == '__main__':
    """Test and verify PPG filter."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test and verify PPG low-pass filter'
    )
    parser.add_argument(
        '--rate',
        type=float,
        default=64.0,
        help='Sampling rate in Hz (default: 64)'
    )
    parser.add_argument(
        '--corner',
        type=float,
        default=5.0,
        help='Corner frequency in Hz (default: 5)'
    )
    parser.add_argument(
        '--order',
        type=int,
        default=2,
        help='Filter order/poles (default: 2)'
    )
    parser.add_argument(
        '--ripple',
        type=float,
        default=0.5,
        help='Passband ripple % (default: 0.5)'
    )
    parser.add_argument(
        '--plot',
        type=str,
        default=None,
        help='Save frequency response plot to file'
    )
    parser.add_argument(
        '--test-signal',
        action='store_true',
        help='Test filter with synthetic PPG-like signal'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("PPG Filter Verification")
    print("="*70 + "\n")
    
    # Create filter
    print("Creating PPG filter...")
    ppg_filter = create_ppg_filter(
        sampling_rate_hz=args.rate,
        corner_freq_hz=args.corner,
        order=args.order,
        ripple_pct=args.ripple,
    )
    
    print(f"{ppg_filter.config}\n")
    
    # Verify filter characteristics
    print("Verifying filter characteristics...")
    metrics = verify_filter(ppg_filter, sampling_rate_hz=args.rate, plot_path=args.plot)
    
    print(f"\nFilter Metrics:")
    print(f"  Corner frequency (-3dB): {metrics['corner_freq_hz']:.2f} Hz")
    print(f"  Attenuation at 10 Hz:    {metrics['attenuation_at_10hz']:.1f} dB")
    print(f"  Attenuation at 20 Hz:    {metrics['attenuation_at_20hz']:.1f} dB")
    print(f"  Passband ripple:         {metrics['passband_ripple_db']:.3f} dB")
    
    if args.plot:
        print(f"\n✓ Frequency response plot saved to: {args.plot}")
    
    # Test with synthetic signal
    if args.test_signal:
        print(f"\nTesting with synthetic PPG-like signal...")
        
        # Generate synthetic PPG signal
        # PPG has fundamental at ~1-2 Hz (heart rate) with harmonics
        duration_s = 10.0
        n_samples = int(args.rate * duration_s)
        t = np.arange(n_samples) / args.rate
        
        # Simulate PPG: fundamental + harmonics + noise
        heart_rate_hz = 1.2  # ~72 BPM
        ppg_clean = (
            1.0 * np.sin(2 * np.pi * heart_rate_hz * t) +
            0.3 * np.sin(2 * np.pi * 2 * heart_rate_hz * t) +
            0.1 * np.sin(2 * np.pi * 3 * heart_rate_hz * t)
        )
        
        # Add high-frequency noise
        np.random.seed(42)
        noise = 0.2 * np.random.randn(n_samples)
        ppg_noisy = ppg_clean + noise
        
        # Filter
        ppg_filtered = ppg_filter.filter(ppg_noisy)
        
        # Compute SNR improvement
        # Signal power (clean PPG)
        signal_power = np.mean(ppg_clean ** 2)
        
        # Noise power before filtering
        noise_before = ppg_noisy - ppg_clean
        noise_power_before = np.mean(noise_before ** 2)
        
        # Noise power after filtering
        noise_after = ppg_filtered - ppg_clean
        noise_power_after = np.mean(noise_after ** 2)
        
        # SNR in dB
        snr_before = 10 * np.log10(signal_power / noise_power_before)
        snr_after = 10 * np.log10(signal_power / noise_power_after)
        snr_improvement = snr_after - snr_before
        
        print(f"\nSynthetic Signal Test Results:")
        print(f"  Duration: {duration_s}s ({n_samples} samples)")
        print(f"  Heart rate: {heart_rate_hz * 60:.0f} BPM ({heart_rate_hz} Hz)")
        print(f"  SNR before filtering: {snr_before:.1f} dB")
        print(f"  SNR after filtering:  {snr_after:.1f} dB")
        print(f"  SNR improvement:      +{snr_improvement:.1f} dB")
        
        # Save plot if requested
        if args.plot:
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
            
            # Raw signal
            axes[0].plot(t, ppg_noisy, 'b-', alpha=0.7, label='Noisy')
            axes[0].plot(t, ppg_clean, 'g--', label='Clean (reference)')
            axes[0].set_ylabel('Amplitude')
            axes[0].set_title('Raw PPG Signal (with noise)')
            axes[0].legend(loc='upper right')
            axes[0].grid(True, alpha=0.3)
            
            # Filtered signal
            axes[1].plot(t, ppg_filtered, 'r-', label='Filtered')
            axes[1].plot(t, ppg_clean, 'g--', label='Clean (reference)')
            axes[1].set_ylabel('Amplitude')
            axes[1].set_title('Filtered PPG Signal')
            axes[1].legend(loc='upper right')
            axes[1].grid(True, alpha=0.3)
            
            # Error
            axes[2].plot(t, ppg_filtered - ppg_clean, 'm-', label='Residual error')
            axes[2].set_ylabel('Error')
            axes[2].set_xlabel('Time (s)')
            axes[2].legend(loc='upper right')
            axes[2].grid(True, alpha=0.3)
            
            plt.tight_layout()
            plot_path_signal = args.plot.replace('.png', '_signal.png')
            plt.savefig(plot_path_signal, dpi=150)
            plt.close()
            print(f"\n✓ Signal test plot saved to: {plot_path_signal}")
    
    print("\n" + "="*70)
    print("✓ Filter verification complete")
    print("="*70 + "\n")
