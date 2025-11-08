"""
DiagnosticsVisualizer Module
============================

Visualization and diagnostic tools for color transfer analysis.

Responsibilities:
- Generate comprehensive visualizations
- Histogram and distribution plots
- 3D color space scatter plots
- Delta E heat maps
- Vector field visualizations
- Statistical comparison plots
- Export reports in multiple formats

Design Principles:
- Factory Pattern: Create different plot types
- Builder Pattern: Configure visualizations
- Strategy Pattern: Multiple export formats
"""

import numpy as np
import cv2
from typing import Optional, List, Dict, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

from .color_space_manager import ColorSpaceManager, ColorSpace
from .color_statistics_engine import ColorStatisticsEngine, ColorStatistics

# Optional matplotlib import
MATPLOTLIB_AVAILABLE = False
try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from mpl_toolkits.mplot3d import Axes3D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    pass

# Optional plotly import (for interactive plots)
PLOTLY_AVAILABLE = False
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    pass


class PlotType(Enum):
    """Available plot types."""
    HISTOGRAM = "histogram"
    CDF = "cdf"
    SCATTER_3D = "scatter_3d"
    DELTA_E_MAP = "delta_e_map"
    VECTOR_FIELD = "vector_field"
    SIDE_BY_SIDE = "side_by_side"
    STATISTICS = "statistics"


class ExportFormat(Enum):
    """Export formats for visualizations."""
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"
    HTML = "html"  # For interactive plots


@dataclass
class VisualizationConfig:
    """
    Configuration for visualizations.

    Attributes:
    ----------
    figsize : Tuple[int, int]
        Figure size in inches
    dpi : int
        Dots per inch for raster outputs
    style : str
        Matplotlib style ('seaborn', 'ggplot', etc.)
    interactive : bool
        Use interactive plots (Plotly) if available
    show_stats : bool
        Show statistical annotations
    colormap : str
        Colormap for heat maps
    """
    figsize: Tuple[int, int] = (12, 8)
    dpi: int = 150
    style: str = 'seaborn-v0_8-darkgrid'
    interactive: bool = False
    show_stats: bool = True
    colormap: str = 'viridis'


class DiagnosticsVisualizer:
    """
    Visualization engine for color transfer diagnostics.

    This class provides comprehensive visualization tools for analyzing
    color transfer results, including histograms, 3D plots, and statistical
    comparisons.

    Example:
    -------
    >>> viz = DiagnosticsVisualizer()
    >>> fig = viz.plot_histogram_comparison(source, target, result)
    >>> viz.save_figure(fig, 'histogram.png')
    """

    def __init__(self, config: Optional[VisualizationConfig] = None):
        """
        Initialize DiagnosticsVisualizer.

        Parameters:
        ----------
        config : Optional[VisualizationConfig]
            Visualization configuration
        """
        self.config = config or VisualizationConfig()
        self.color_manager = ColorSpaceManager()
        self.stats_engine = ColorStatisticsEngine()

        # Check dependencies
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("Matplotlib is required for visualizations. "
                            "Install with: pip install matplotlib")

        # Set matplotlib style
        try:
            plt.style.use(self.config.style)
        except:
            # Fallback to default if style not available
            pass

    # ============================================================================
    # Histogram Visualizations
    # ============================================================================

    def plot_histogram_comparison(self,
                                  source: np.ndarray,
                                  target: np.ndarray,
                                  result: np.ndarray,
                                  color_space: ColorSpace = ColorSpace.LAB,
                                  bins: int = 256,
                                  save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot histogram comparison for source, target, and result.

        Parameters:
        ----------
        source : np.ndarray
            Source image (BGR uint8)
        target : np.ndarray
            Target image (BGR uint8)
        result : np.ndarray
            Result image (BGR uint8)
        color_space : ColorSpace
            Color space for analysis
        bins : int
            Number of histogram bins
        save_path : Optional[str]
            Path to save figure

        Returns:
        -------
        plt.Figure
            Matplotlib figure
        """
        # Convert to specified color space
        source_cs = self.color_manager.convert_to(
            self.color_manager.to_float(source), color_space
        )
        target_cs = self.color_manager.convert_to(
            self.color_manager.to_float(target), color_space
        )
        result_cs = self.color_manager.convert_to(
            self.color_manager.to_float(result), color_space
        )

        # Get channel names
        channel_names = self.color_manager.get_channel_names(color_space)

        # Create figure
        fig, axes = plt.subplots(1, 3, figsize=self.config.figsize)
        fig.suptitle(f'Histogram Comparison ({color_space.value} space)',
                    fontsize=16, fontweight='bold')

        # Plot each channel
        for i, (ax, name) in enumerate(zip(axes, channel_names)):
            # Extract channels
            src_ch = source_cs[:, :, i].flatten()
            tgt_ch = target_cs[:, :, i].flatten()
            res_ch = result_cs[:, :, i].flatten()

            # Plot histograms
            ax.hist(src_ch, bins=bins, alpha=0.5, label='Source',
                   color='red', density=True, histtype='stepfilled')
            ax.hist(tgt_ch, bins=bins, alpha=0.5, label='Target',
                   color='blue', density=True, histtype='stepfilled')
            ax.hist(res_ch, bins=bins, alpha=0.5, label='Result',
                   color='green', density=True, histtype='stepfilled')

            # Add mean lines
            ax.axvline(np.mean(src_ch), color='darkred', linestyle='--',
                      linewidth=2, label=f'μ_src={np.mean(src_ch):.2f}')
            ax.axvline(np.mean(res_ch), color='darkgreen', linestyle='--',
                      linewidth=2, label=f'μ_res={np.mean(res_ch):.2f}')

            ax.set_xlabel(name, fontsize=12, fontweight='bold')
            ax.set_ylabel('Density', fontsize=12)
            ax.legend(fontsize=9, loc='upper right')
            ax.grid(alpha=0.3)

        plt.tight_layout()

        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_cdf_comparison(self,
                           source: np.ndarray,
                           target: np.ndarray,
                           result: np.ndarray,
                           color_space: ColorSpace = ColorSpace.LAB,
                           save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot cumulative distribution function comparison.

        Parameters:
        ----------
        source, target, result : np.ndarray
            Images to compare
        color_space : ColorSpace
            Color space for analysis
        save_path : Optional[str]
            Path to save figure

        Returns:
        -------
        plt.Figure
            Matplotlib figure
        """
        # Convert to color space
        source_cs = self.color_manager.convert_to(
            self.color_manager.to_float(source), color_space
        )
        target_cs = self.color_manager.convert_to(
            self.color_manager.to_float(target), color_space
        )
        result_cs = self.color_manager.convert_to(
            self.color_manager.to_float(result), color_space
        )

        channel_names = self.color_manager.get_channel_names(color_space)

        fig, axes = plt.subplots(1, 3, figsize=self.config.figsize)
        fig.suptitle(f'CDF Comparison ({color_space.value} space)',
                    fontsize=16, fontweight='bold')

        for i, (ax, name) in enumerate(zip(axes, channel_names)):
            # Extract channels
            src_ch = source_cs[:, :, i].flatten()
            tgt_ch = target_cs[:, :, i].flatten()
            res_ch = result_cs[:, :, i].flatten()

            # Compute CDFs
            src_sorted = np.sort(src_ch)
            tgt_sorted = np.sort(tgt_ch)
            res_sorted = np.sort(res_ch)

            src_cdf = np.arange(len(src_sorted)) / len(src_sorted)
            tgt_cdf = np.arange(len(tgt_sorted)) / len(tgt_sorted)
            res_cdf = np.arange(len(res_sorted)) / len(res_sorted)

            # Plot CDFs
            ax.plot(src_sorted, src_cdf, 'r-', label='Source', linewidth=2)
            ax.plot(tgt_sorted, tgt_cdf, 'b-', label='Target', linewidth=2)
            ax.plot(res_sorted, res_cdf, 'g-', label='Result', linewidth=2)

            ax.set_xlabel(name, fontsize=12, fontweight='bold')
            ax.set_ylabel('Cumulative Probability', fontsize=12)
            ax.legend(fontsize=10)
            ax.grid(alpha=0.3)

        plt.tight_layout()

        if save_path:
            self.save_figure(fig, save_path)

        return fig

    # ============================================================================
    # 3D Visualizations
    # ============================================================================

    def plot_3d_color_space(self,
                           image: np.ndarray,
                           title: str = "Color Distribution",
                           color_space: ColorSpace = ColorSpace.LAB,
                           sample_size: int = 5000,
                           save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot 3D scatter of pixel colors in specified color space.

        Parameters:
        ----------
        image : np.ndarray
            Image to visualize
        title : str
            Plot title
        color_space : ColorSpace
            Color space for visualization
        sample_size : int
            Number of pixels to sample (for performance)
        save_path : Optional[str]
            Path to save figure

        Returns:
        -------
        plt.Figure
            Matplotlib figure
        """
        # Convert to color space
        image_cs = self.color_manager.convert_to(
            self.color_manager.to_float(image), color_space
        )

        # Reshape to pixel array
        pixels = image_cs.reshape(-1, 3)

        # Sample if too many pixels
        if pixels.shape[0] > sample_size:
            indices = np.random.choice(pixels.shape[0], sample_size, replace=False)
            pixels = pixels[indices]

        # Create figure
        fig = plt.figure(figsize=self.config.figsize)
        ax = fig.add_subplot(111, projection='3d')

        # Get channel names
        channel_names = self.color_manager.get_channel_names(color_space)

        # Create colors for points (approximate RGB from color space)
        # This is a simplification; proper conversion would be needed
        colors = pixels / np.max(pixels)  # Normalize for display

        # Plot
        ax.scatter(pixels[:, 0], pixels[:, 1], pixels[:, 2],
                  c=colors, s=1, alpha=0.5)

        ax.set_xlabel(channel_names[0], fontsize=12, fontweight='bold')
        ax.set_ylabel(channel_names[1], fontsize=12, fontweight='bold')
        ax.set_zlabel(channel_names[2], fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold')

        plt.tight_layout()

        if save_path:
            self.save_figure(fig, save_path)

        return fig

    def plot_3d_comparison(self,
                          source: np.ndarray,
                          target: np.ndarray,
                          result: np.ndarray,
                          color_space: ColorSpace = ColorSpace.LAB,
                          sample_size: int = 3000,
                          save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot 3D scatter comparison of source, target, and result.

        Parameters:
        ----------
        source, target, result : np.ndarray
            Images to compare
        color_space : ColorSpace
            Color space for visualization
        sample_size : int
            Pixels per image to sample
        save_path : Optional[str]
            Path to save figure

        Returns:
        -------
        plt.Figure
            Matplotlib figure
        """
        # Convert all to color space
        source_cs = self.color_manager.convert_to(
            self.color_manager.to_float(source), color_space
        ).reshape(-1, 3)
        target_cs = self.color_manager.convert_to(
            self.color_manager.to_float(target), color_space
        ).reshape(-1, 3)
        result_cs = self.color_manager.convert_to(
            self.color_manager.to_float(result), color_space
        ).reshape(-1, 3)

        # Sample
        src_sample = source_cs[np.random.choice(len(source_cs), sample_size)]
        tgt_sample = target_cs[np.random.choice(len(target_cs), sample_size)]
        res_sample = result_cs[np.random.choice(len(result_cs), sample_size)]

        # Create figure
        fig = plt.figure(figsize=(15, 5))
        channel_names = self.color_manager.get_channel_names(color_space)

        # Three subplots
        for i, (data, title, color) in enumerate([
            (src_sample, 'Source', 'red'),
            (tgt_sample, 'Target', 'blue'),
            (res_sample, 'Result', 'green')
        ]):
            ax = fig.add_subplot(1, 3, i+1, projection='3d')
            ax.scatter(data[:, 0], data[:, 1], data[:, 2],
                      c=color, s=1, alpha=0.3)
            ax.set_xlabel(channel_names[0])
            ax.set_ylabel(channel_names[1])
            ax.set_zlabel(channel_names[2])
            ax.set_title(title, fontweight='bold')

        plt.tight_layout()

        if save_path:
            self.save_figure(fig, save_path)

        return fig

    # ============================================================================
    # Delta E Visualization
    # ============================================================================

    def plot_delta_e_map(self,
                        original: np.ndarray,
                        transformed: np.ndarray,
                        save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot Delta E heat map showing perceptual differences.

        Parameters:
        ----------
        original : np.ndarray
            Original image (BGR uint8)
        transformed : np.ndarray
            Transformed image (BGR uint8)
        save_path : Optional[str]
            Path to save figure

        Returns:
        -------
        plt.Figure
            Matplotlib figure
        """
        # Convert to Lab for Delta E computation
        orig_lab = self.color_manager.convert_to(
            self.color_manager.to_float(original), ColorSpace.LAB
        )
        trans_lab = self.color_manager.convert_to(
            self.color_manager.to_float(transformed), ColorSpace.LAB
        )

        # Compute Delta E (CIE76)
        delta_e = np.sqrt(np.sum((orig_lab - trans_lab)**2, axis=2))

        # Create figure
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        # Original image
        axes[0].imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
        axes[0].set_title('Original', fontsize=14, fontweight='bold')
        axes[0].axis('off')

        # Transformed image
        axes[1].imshow(cv2.cvtColor(transformed, cv2.COLOR_BGR2RGB))
        axes[1].set_title('Transformed', fontsize=14, fontweight='bold')
        axes[1].axis('off')

        # Delta E map
        im = axes[2].imshow(delta_e, cmap=self.config.colormap)
        axes[2].set_title(f'ΔE Map (avg: {np.mean(delta_e):.2f})',
                         fontsize=14, fontweight='bold')
        axes[2].axis('off')

        # Add colorbar
        cbar = plt.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04)
        cbar.set_label('ΔE (perceptual difference)', rotation=270, labelpad=20)

        plt.tight_layout()

        if save_path:
            self.save_figure(fig, save_path)

        return fig

    # ============================================================================
    # Side-by-Side Comparison
    # ============================================================================

    def plot_side_by_side(self,
                         source: np.ndarray,
                         target: np.ndarray,
                         result: np.ndarray,
                         titles: Optional[List[str]] = None,
                         save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot source, target, and result side by side.

        Parameters:
        ----------
        source, target, result : np.ndarray
            Images to display
        titles : Optional[List[str]]
            Custom titles
        save_path : Optional[str]
            Path to save figure

        Returns:
        -------
        plt.Figure
            Matplotlib figure
        """
        if titles is None:
            titles = ['Source', 'Target', 'Result']

        fig, axes = plt.subplots(1, 3, figsize=self.config.figsize)

        for ax, img, title in zip(axes, [source, target, result], titles):
            ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.axis('off')

        plt.tight_layout()

        if save_path:
            self.save_figure(fig, save_path)

        return fig

    # ============================================================================
    # Statistical Visualization
    # ============================================================================

    def plot_statistics_comparison(self,
                                   source_stats: ColorStatistics,
                                   target_stats: ColorStatistics,
                                   result_stats: ColorStatistics,
                                   channel_names: Optional[List[str]] = None,
                                   save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot statistical comparison (mean, std) across channels.

        Parameters:
        ----------
        source_stats, target_stats, result_stats : ColorStatistics
            Statistics to compare
        channel_names : Optional[List[str]]
            Channel names
        save_path : Optional[str]
            Path to save figure

        Returns:
        -------
        plt.Figure
            Matplotlib figure
        """
        if channel_names is None:
            channel_names = [f'Ch{i}' for i in range(source_stats.num_channels)]

        fig, axes = plt.subplots(1, 2, figsize=self.config.figsize)

        x = np.arange(len(channel_names))
        width = 0.25

        # Mean comparison
        axes[0].bar(x - width, source_stats.mean, width, label='Source', color='red', alpha=0.7)
        axes[0].bar(x, target_stats.mean, width, label='Target', color='blue', alpha=0.7)
        axes[0].bar(x + width, result_stats.mean, width, label='Result', color='green', alpha=0.7)
        axes[0].set_xlabel('Channel', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('Mean', fontsize=12, fontweight='bold')
        axes[0].set_title('Mean Comparison', fontsize=14, fontweight='bold')
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(channel_names)
        axes[0].legend()
        axes[0].grid(alpha=0.3)

        # Std comparison
        axes[1].bar(x - width, source_stats.std, width, label='Source', color='red', alpha=0.7)
        axes[1].bar(x, target_stats.std, width, label='Target', color='blue', alpha=0.7)
        axes[1].bar(x + width, result_stats.std, width, label='Result', color='green', alpha=0.7)
        axes[1].set_xlabel('Channel', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('Standard Deviation', fontsize=12, fontweight='bold')
        axes[1].set_title('Std Deviation Comparison', fontsize=14, fontweight='bold')
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(channel_names)
        axes[1].legend()
        axes[1].grid(alpha=0.3)

        plt.tight_layout()

        if save_path:
            self.save_figure(fig, save_path)

        return fig

    # ============================================================================
    # Comprehensive Report
    # ============================================================================

    def generate_comprehensive_report(self,
                                     source: np.ndarray,
                                     target: np.ndarray,
                                     result: np.ndarray,
                                     output_dir: str = '.') -> Dict[str, str]:
        """
        Generate comprehensive diagnostic report with all visualizations.

        Parameters:
        ----------
        source, target, result : np.ndarray
            Images to analyze
        output_dir : str
            Output directory for figures

        Returns:
        -------
        Dict[str, str]
            Dictionary mapping plot type to file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        generated_files = {}

        # Histogram comparison
        fig = self.plot_histogram_comparison(source, target, result)
        path = output_path / 'histogram_comparison.png'
        self.save_figure(fig, str(path))
        generated_files['histogram'] = str(path)
        plt.close(fig)

        # CDF comparison
        fig = self.plot_cdf_comparison(source, target, result)
        path = output_path / 'cdf_comparison.png'
        self.save_figure(fig, str(path))
        generated_files['cdf'] = str(path)
        plt.close(fig)

        # 3D scatter
        fig = self.plot_3d_comparison(source, target, result)
        path = output_path / '3d_comparison.png'
        self.save_figure(fig, str(path))
        generated_files['3d_scatter'] = str(path)
        plt.close(fig)

        # Delta E map
        fig = self.plot_delta_e_map(target, result)
        path = output_path / 'delta_e_map.png'
        self.save_figure(fig, str(path))
        generated_files['delta_e'] = str(path)
        plt.close(fig)

        # Side by side
        fig = self.plot_side_by_side(source, target, result)
        path = output_path / 'side_by_side.png'
        self.save_figure(fig, str(path))
        generated_files['side_by_side'] = str(path)
        plt.close(fig)

        # Statistics
        source_lab = self.color_manager.convert_to(
            self.color_manager.to_float(source), ColorSpace.LAB
        )
        target_lab = self.color_manager.convert_to(
            self.color_manager.to_float(target), ColorSpace.LAB
        )
        result_lab = self.color_manager.convert_to(
            self.color_manager.to_float(result), ColorSpace.LAB
        )

        source_stats = self.stats_engine.compute_stats(source_lab)
        target_stats = self.stats_engine.compute_stats(target_lab)
        result_stats = self.stats_engine.compute_stats(result_lab)

        fig = self.plot_statistics_comparison(
            source_stats, target_stats, result_stats,
            channel_names=['L*', 'a*', 'b*']
        )
        path = output_path / 'statistics_comparison.png'
        self.save_figure(fig, str(path))
        generated_files['statistics'] = str(path)
        plt.close(fig)

        return generated_files

    # ============================================================================
    # Utility Methods
    # ============================================================================

    def save_figure(self, fig: plt.Figure, path: str, format: Optional[str] = None):
        """
        Save figure to file.

        Parameters:
        ----------
        fig : plt.Figure
            Matplotlib figure
        path : str
            Output path
        format : Optional[str]
            Output format (inferred from path if None)
        """
        if format is None:
            format = Path(path).suffix[1:]  # Remove dot

        fig.savefig(path, dpi=self.config.dpi, bbox_inches='tight', format=format)


# Convenience function
def visualize_transfer(source: np.ndarray,
                      target: np.ndarray,
                      result: np.ndarray,
                      output_dir: str = '.') -> Dict[str, str]:
    """
    Quick visualization of transfer results.

    Parameters:
    ----------
    source, target, result : np.ndarray
        Images to visualize
    output_dir : str
        Output directory

    Returns:
    -------
    Dict[str, str]
        Generated file paths

    Example:
    -------
    >>> files = visualize_transfer(source, target, result, 'output/')
    >>> print(files['histogram'])  # 'output/histogram_comparison.png'
    """
    viz = DiagnosticsVisualizer()
    return viz.generate_comprehensive_report(source, target, result, output_dir)
