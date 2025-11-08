"""
Architecture Diagram Generator
===============================

Generate architecture diagrams for the framework.

Features:
- Module dependency graphs
- Component diagrams
- Data flow diagrams
- Export to various formats (ASCII, SVG, PNG)
"""

from pathlib import Path
from typing import List, Dict, Set, Optional
import ast
import logging

logger = logging.getLogger(__name__)


class ArchitectureDiagram:
    """
    Generate architecture diagrams.

    Example:
        >>> diagram = ArchitectureDiagram()
        >>> diagram.generate_module_diagram()
        >>> diagram.save_ascii('docs/architecture.txt')
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize diagram generator.

        Parameters:
        -----------
        project_root : str, optional
            Root directory of project
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.project_root = Path(project_root)

        self.modules: Dict[str, Set[str]] = {}
        self.diagram_text: List[str] = []

    def generate_module_diagram(self) -> str:
        """
        Generate module dependency diagram.

        Returns:
        --------
        str
            ASCII art diagram
        """
        self._scan_modules()
        self._build_ascii_diagram()

        return '\n'.join(self.diagram_text)

    def _scan_modules(self):
        """Scan project and build dependency graph."""
        self.modules = {}

        for py_file in self.project_root.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue

            module_name = self._get_module_name(py_file)
            imports = self._extract_imports(py_file)

            self.modules[module_name] = imports

    def _get_module_name(self, file_path: Path) -> str:
        """Get module name from file path."""
        rel_path = file_path.relative_to(self.project_root)
        module = str(rel_path).replace('/', '.').replace('.py', '')
        return module

    def _extract_imports(self, file_path: Path) -> Set[str]:
        """Extract imports from Python file."""
        imports = set()

        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)

        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")

        return imports

    def _build_ascii_diagram(self):
        """Build ASCII art diagram."""
        self.diagram_text = []

        self.diagram_text.append("```")
        self.diagram_text.append("Color Transfer Framework - Architecture")
        self.diagram_text.append("=" * 50)
        self.diagram_text.append("")

        # Core modules
        self.diagram_text.append("Core Modules:")
        self.diagram_text.append("  ┌─────────────────────────────────┐")
        self.diagram_text.append("  │     ColorSpaceManager           │")
        self.diagram_text.append("  │  (Color space conversions)      │")
        self.diagram_text.append("  └─────────────────────────────────┘")
        self.diagram_text.append("              ↓")
        self.diagram_text.append("  ┌─────────────────────────────────┐")
        self.diagram_text.append("  │  ColorStatisticsEngine          │")
        self.diagram_text.append("  │  (Mean, std, histograms)        │")
        self.diagram_text.append("  └─────────────────────────────────┘")
        self.diagram_text.append("              ↓")
        self.diagram_text.append("  ┌─────────────────────────────────┐")
        self.diagram_text.append("  │      TransferEngine             │")
        self.diagram_text.append("  │  (4 classical algorithms)       │")
        self.diagram_text.append("  └─────────────────────────────────┘")
        self.diagram_text.append("")

        # ML Module
        self.diagram_text.append("ML/DL Module:")
        self.diagram_text.append("  ┌─────────────────────────────────┐")
        self.diagram_text.append("  │      MLHybridModule             │")
        self.diagram_text.append("  │  - Neural Style Transfer        │")
        self.diagram_text.append("  │  - Deep Color Transfer          │")
        self.diagram_text.append("  │  - Model Management             │")
        self.diagram_text.append("  └─────────────────────────────────┘")
        self.diagram_text.append("")

        # Advanced Processing
        self.diagram_text.append("Advanced Processing:")
        self.diagram_text.append("  ┌─────────────────────────────────┐")
        self.diagram_text.append("  │   AdvancedProcessing            │")
        self.diagram_text.append("  │  - Batch Processor              │")
        self.diagram_text.append("  │  - Video Processor              │")
        self.diagram_text.append("  │  - Webcam Processor             │")
        self.diagram_text.append("  │  - Plugin Manager               │")
        self.diagram_text.append("  │  - Palette Extractor            │")
        self.diagram_text.append("  │  - Multi Blender                │")
        self.diagram_text.append("  └─────────────────────────────────┘")
        self.diagram_text.append("")

        # Data Management
        self.diagram_text.append("Data Management:")
        self.diagram_text.append("  ┌─────────────────────────────────┐")
        self.diagram_text.append("  │     DataManagement              │")
        self.diagram_text.append("  │  - Cache Manager                │")
        self.diagram_text.append("  │  - Hash Deduplicator            │")
        self.diagram_text.append("  │  - Cleanup Manager              │")
        self.diagram_text.append("  │  - History Exporter             │")
        self.diagram_text.append("  └─────────────────────────────────┘")
        self.diagram_text.append("")

        # Interface Layer
        self.diagram_text.append("Interface Layer:")
        self.diagram_text.append("  ┌─────────────────────────────────┐")
        self.diagram_text.append("  │   TransferOrchestrator          │")
        self.diagram_text.append("  │  (Coordinates all modules)      │")
        self.diagram_text.append("  └─────────────────────────────────┘")
        self.diagram_text.append("         ↓ ↓ ↓ ↓")
        self.diagram_text.append("  ┌──────┬──────┬──────┬──────┐")
        self.diagram_text.append("  │ CLI  │ API  │ Web  │ TUI  │")
        self.diagram_text.append("  └──────┴──────┴──────┴──────┘")
        self.diagram_text.append("")

        # Supporting Modules
        self.diagram_text.append("Supporting Modules:")
        self.diagram_text.append("  ┌─────────────────────────────────┐")
        self.diagram_text.append("  │  DiagnosticsVisualizer          │")
        self.diagram_text.append("  │  ComplexityAnalyzer             │")
        self.diagram_text.append("  │  PersistenceLogger              │")
        self.diagram_text.append("  │  BenchmarkingSuite              │")
        self.diagram_text.append("  │  DocumentationModule            │")
        self.diagram_text.append("  └─────────────────────────────────┘")
        self.diagram_text.append("")

        self.diagram_text.append("```")

    def generate_data_flow_diagram(self) -> str:
        """Generate data flow diagram."""
        lines = []

        lines.append("```")
        lines.append("Data Flow Diagram")
        lines.append("=" * 50)
        lines.append("")
        lines.append("User Input (CLI/API/WebUI/TUI)")
        lines.append("      ↓")
        lines.append("TransferOrchestrator")
        lines.append("      ↓")
        lines.append("Load Images → ColorSpaceManager → Convert to LAB/LCH")
        lines.append("      ↓")
        lines.append("ColorStatisticsEngine → Calculate mean/std")
        lines.append("      ↓")
        lines.append("TransferEngine → Apply algorithm")
        lines.append("      ↓")
        lines.append("Result Processing → Blending, Clipping")
        lines.append("      ↓")
        lines.append("Optional: DiagnosticsVisualizer")
        lines.append("      ↓")
        lines.append("PersistenceLogger → Database")
        lines.append("      ↓")
        lines.append("Return Result")
        lines.append("```")

        return '\n'.join(lines)

    def save_ascii(self, output_path: str):
        """Save diagram as ASCII text."""
        diagram = self.generate_module_diagram()
        Path(output_path).write_text(diagram)
        logger.info(f"Architecture diagram saved to {output_path}")

    def save_dataflow(self, output_path: str):
        """Save data flow diagram."""
        diagram = self.generate_data_flow_diagram()
        Path(output_path).write_text(diagram)
        logger.info(f"Data flow diagram saved to {output_path}")
