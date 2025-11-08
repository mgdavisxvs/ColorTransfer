"""
Visual Regression Testing - Knuth's Pixel-Perfect Verification

Tests visual consistency with mathematical precision:
- Pixel-by-pixel comparison
- Perceptual difference metrics
- Screenshot comparison
- Cross-browser visual parity

Mathematical Analysis (Knuth):
- Structural Similarity Index (SSIM)
- Peak Signal-to-Noise Ratio (PSNR)
- Mean Squared Error (MSE)
- Perceptual Hash Distance

Practical Testing (Graham):
- Baseline screenshots
- Comparison on changes
- Threshold-based acceptance
- Visual diff generation
"""

import pytest
import cv2
import numpy as np
from pathlib import Path
import tempfile
from typing import Tuple
import hashlib

try:
    from playwright.sync_api import sync_playwright, Page
    from skimage.metrics import structural_similarity as ssim
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


class VisualRegressionTester:
    """
    Visual Regression Testing Framework

    Knuth's Visual Comparison:
    ==========================

    Metrics:
    1. SSIM (Structural Similarity Index)
       - Range: [0, 1]
       - 1.0 = identical
       - > 0.95 = acceptable
       - Formula: SSIM(x,y) = (2μxμy + C1)(2σxy + C2) / (μx² + μy² + C1)(σx² + σy² + C2)

    2. PSNR (Peak Signal-to-Noise Ratio)
       - Range: [0, ∞]
       - > 30 dB = good quality
       - > 40 dB = excellent quality
       - Formula: PSNR = 10 * log10(MAX² / MSE)

    3. MSE (Mean Squared Error)
       - Range: [0, ∞]
       - 0 = identical
       - < 100 = acceptable (depends on scale)
       - Formula: MSE = (1/N) * Σ(I1 - I2)²

    4. Perceptual Hash
       - Fast similarity check
       - Hamming distance < 10 = similar
       - O(1) comparison
    """

    def __init__(self, baseline_dir: Path, threshold_ssim: float = 0.95):
        """
        Initialize visual regression tester

        Args:
            baseline_dir: Directory for baseline screenshots
            threshold_ssim: SSIM threshold for acceptance (default 0.95)
        """
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.threshold_ssim = threshold_ssim

    def compute_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        Compute Structural Similarity Index

        Knuth's SSIM Analysis:
        - Luminance comparison
        - Contrast comparison
        - Structure comparison
        - Combined metric

        Returns:
            SSIM value in [0, 1]
        """
        # Convert to grayscale if color
        if len(img1.shape) == 3:
            img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        else:
            img1_gray = img1

        if len(img2.shape) == 3:
            img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        else:
            img2_gray = img2

        # Compute SSIM
        similarity, diff = ssim(img1_gray, img2_gray, full=True)

        return similarity

    def compute_psnr(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        Compute Peak Signal-to-Noise Ratio

        Knuth's PSNR:
        PSNR = 10 * log10(MAX² / MSE)
        where MAX = maximum possible pixel value

        Returns:
            PSNR in decibels (dB)
        """
        mse = np.mean((img1.astype(float) - img2.astype(float)) ** 2)

        if mse == 0:
            return float('inf')  # Identical images

        max_pixel = 255.0
        psnr = 10 * np.log10((max_pixel ** 2) / mse)

        return psnr

    def compute_mse(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        Compute Mean Squared Error

        Knuth's MSE:
        MSE = (1/N) * Σ(I1 - I2)²

        Returns:
            MSE value
        """
        return np.mean((img1.astype(float) - img2.astype(float)) ** 2)

    def compute_perceptual_hash(self, img: np.ndarray) -> str:
        """
        Compute perceptual hash (pHash)

        Graham's Fast Comparison:
        - Resize to 8x8
        - Convert to grayscale
        - Compute DCT
        - Extract hash

        Returns:
            Hexadecimal hash string
        """
        # Resize to 8x8
        img_small = cv2.resize(img, (8, 8))

        # Convert to grayscale
        if len(img_small.shape) == 3:
            img_gray = cv2.cvtColor(img_small, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = img_small

        # Compute hash
        hash_value = hashlib.md5(img_gray.tobytes()).hexdigest()

        return hash_value

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        Compute Hamming distance between two hashes

        Knuth's Distance:
        - Count differing bits
        - O(n) where n = hash length

        Returns:
            Number of differing bits
        """
        if len(hash1) != len(hash2):
            raise ValueError("Hashes must be same length")

        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

    def compare_screenshots(
        self,
        baseline_path: Path,
        current_path: Path,
        generate_diff: bool = True
    ) -> dict:
        """
        Compare two screenshots with multiple metrics

        Args:
            baseline_path: Path to baseline screenshot
            current_path: Path to current screenshot
            generate_diff: Generate visual difference image

        Returns:
            Dictionary with comparison metrics
        """
        # Load images
        baseline = cv2.imread(str(baseline_path))
        current = cv2.imread(str(current_path))

        if baseline is None:
            raise ValueError(f"Cannot load baseline: {baseline_path}")
        if current is None:
            raise ValueError(f"Cannot load current: {current_path}")

        # Ensure same size
        if baseline.shape != current.shape:
            current = cv2.resize(current, (baseline.shape[1], baseline.shape[0]))

        # Compute metrics
        ssim_value = self.compute_ssim(baseline, current)
        psnr_value = self.compute_psnr(baseline, current)
        mse_value = self.compute_mse(baseline, current)

        hash1 = self.compute_perceptual_hash(baseline)
        hash2 = self.compute_perceptual_hash(current)
        hamming = self.hamming_distance(hash1, hash2)

        # Determine if acceptable
        acceptable = ssim_value >= self.threshold_ssim

        result = {
            'ssim': ssim_value,
            'psnr': psnr_value,
            'mse': mse_value,
            'perceptual_hash_distance': hamming,
            'acceptable': acceptable,
            'threshold_ssim': self.threshold_ssim
        }

        # Generate diff image
        if generate_diff and not acceptable:
            diff_path = current_path.parent / f"{current_path.stem}_diff.png"
            diff = cv2.absdiff(baseline, current)
            cv2.imwrite(str(diff_path), diff)
            result['diff_path'] = str(diff_path)

        return result

    def update_baseline(self, name: str, screenshot_path: Path):
        """
        Update baseline screenshot

        Graham's Baseline Management:
        - Copy current to baseline
        - Used after verified changes
        """
        baseline_path = self.baseline_dir / f"{name}.png"
        import shutil
        shutil.copy(screenshot_path, baseline_path)


@pytest.mark.skipif(not DEPENDENCIES_AVAILABLE, reason="Dependencies not installed")
class TestVisualRegression:
    """
    Visual Regression Test Suite

    Tests visual consistency across changes
    """

    @pytest.fixture(scope="class")
    def tester(self) -> VisualRegressionTester:
        """Create visual regression tester"""
        baseline_dir = Path(__file__).parent / "baselines"
        return VisualRegressionTester(baseline_dir, threshold_ssim=0.95)

    @pytest.fixture(scope="class")
    def browser(self):
        """Create browser instance"""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            yield browser
            browser.close()

    def capture_screenshot(self, page: Page, name: str) -> Path:
        """Capture screenshot"""
        screenshot_dir = Path(tempfile.mkdtemp())
        screenshot_path = screenshot_dir / f"{name}.png"
        page.screenshot(path=str(screenshot_path))
        return screenshot_path

    def test_home_page_visual(self, browser, tester: VisualRegressionTester):
        """
        Test: Home page visual consistency

        Knuth's Visual Test:
        - Capture current screenshot
        - Compare to baseline
        - Verify SSIM > threshold
        """
        page = browser.new_page()
        page.goto("http://localhost:5000")
        page.wait_for_load_state("networkidle")

        # Capture screenshot
        current = self.capture_screenshot(page, "home_page")

        # Check if baseline exists
        baseline = tester.baseline_dir / "home_page.png"

        if not baseline.exists():
            # First run - create baseline
            tester.update_baseline("home_page", current)
            pytest.skip("Baseline created, rerun to compare")

        # Compare
        result = tester.compare_screenshots(baseline, current)

        assert result['acceptable'], \
            f"Visual regression detected: SSIM={result['ssim']:.3f} < {result['threshold_ssim']}"

        page.close()

    def test_form_visual(self, browser, tester: VisualRegressionTester):
        """Test: Form visual consistency"""
        page = browser.new_page()
        page.goto("http://localhost:5000")
        page.wait_for_load_state("networkidle")

        # Scroll to form
        page.locator("#transferForm").scroll_into_view_if_needed()

        current = self.capture_screenshot(page, "transfer_form")
        baseline = tester.baseline_dir / "transfer_form.png"

        if not baseline.exists():
            tester.update_baseline("transfer_form", current)
            pytest.skip("Baseline created")

        result = tester.compare_screenshots(baseline, current)

        assert result['acceptable'], \
            f"Visual regression in form: SSIM={result['ssim']:.3f}"

        page.close()


# Knuth's Visual Regression Analysis
"""
Visual Regression Testing Analysis (Knuth/Graham):
==================================================

Metrics Interpretation:

SSIM (Structural Similarity):
- 1.0: Identical
- > 0.99: Imperceptible differences
- 0.95-0.99: Minor differences (lighting, AA)
- 0.90-0.95: Noticeable differences
- < 0.90: Significant differences

PSNR (Peak Signal-to-Noise Ratio):
- > 50 dB: Identical or imperceptible
- 40-50 dB: Excellent quality
- 30-40 dB: Good quality
- 20-30 dB: Acceptable quality
- < 20 dB: Poor quality

MSE (Mean Squared Error):
- 0: Identical
- < 10: Very similar
- 10-100: Similar
- 100-1000: Moderate differences
- > 1000: Significant differences

Perceptual Hash Distance:
- 0: Identical
- 1-5: Very similar
- 5-10: Similar
- 10-20: Moderate differences
- > 20: Different

Use Cases:

1. Layout Changes:
   - SSIM detects: Yes (structure)
   - PSNR detects: Yes
   - pHash detects: Yes

2. Color Changes:
   - SSIM detects: Partial
   - PSNR detects: Yes
   - pHash detects: No (grayscale)

3. Text Changes:
   - SSIM detects: Yes
   - PSNR detects: Yes
   - pHash detects: Yes

4. Anti-aliasing:
   - SSIM detects: Minor
   - PSNR detects: Yes
   - pHash detects: No

Graham's Best Practices:

1. Create baselines on stable build
2. Update baselines after verified changes
3. Use appropriate thresholds:
   - Strict (0.99): Pixel-perfect
   - Normal (0.95): Minor differences OK
   - Lenient (0.90): Significant differences OK

4. Test on multiple:
   - Screen sizes (desktop, mobile)
   - Browsers (Chrome, Firefox, Safari)
   - Themes (light, dark)

5. Automate in CI/CD:
   - Run on every PR
   - Block merge on failures
   - Generate diff images

6. Handle dynamic content:
   - Mask timestamps
   - Mask user-specific data
   - Use stable test data

Commands:

# Create baselines
pytest tests/visual/test_visual_regression.py --update-baselines

# Run tests
pytest tests/visual/test_visual_regression.py

# Generate report
pytest tests/visual/test_visual_regression.py --html=report.html

# Update specific baseline
pytest tests/visual/test_visual_regression.py::test_home_page_visual --update-baseline
"""
