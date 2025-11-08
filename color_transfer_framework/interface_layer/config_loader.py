"""
Configuration File Loader
=========================

Support for YAML and JSON configuration files.

Allows users to save and load transfer configurations for reproducibility.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from ..transfer_engine import TransferConfig, TransferAlgorithm


@dataclass
class TransferRecipe:
    """Complete transfer recipe including configuration and metadata."""
    name: str
    description: str
    config: Dict[str, Any]
    created_at: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[list] = None


class ConfigLoader:
    """
    Load and save transfer configurations from YAML/JSON files.

    Supports:
    - YAML format (.yaml, .yml)
    - JSON format (.json)
    - Recipe management (named configurations with metadata)
    """

    @staticmethod
    def load_config(config_path: str) -> TransferConfig:
        """
        Load configuration from file.

        Parameters:
        ----------
        config_path : str
            Path to YAML or JSON config file

        Returns:
        -------
        TransferConfig
            Loaded configuration

        Raises:
        ------
        ValueError
            If file format is unsupported or config is invalid
        FileNotFoundError
            If config file doesn't exist
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Determine format from extension
        if path.suffix.lower() in ['.yaml', '.yml']:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
        elif path.suffix.lower() == '.json':
            with open(path, 'r') as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}. Use .yaml, .yml, or .json")

        # Extract config if it's wrapped in a recipe
        if 'config' in data:
            config_data = data['config']
        else:
            config_data = data

        # Build TransferConfig
        return ConfigLoader._build_config(config_data)

    @staticmethod
    def save_config(config: TransferConfig, output_path: str, recipe: Optional[TransferRecipe] = None):
        """
        Save configuration to file.

        Parameters:
        ----------
        config : TransferConfig
            Configuration to save
        output_path : str
            Path to save file
        recipe : TransferRecipe, optional
            Recipe metadata to include
        """
        path = Path(output_path)

        # Convert config to dict
        config_dict = config.to_dict()

        # Wrap in recipe if provided
        if recipe:
            data = {
                'name': recipe.name,
                'description': recipe.description,
                'config': config_dict,
                'created_at': recipe.created_at,
                'author': recipe.author,
                'tags': recipe.tags
            }
        else:
            data = config_dict

        # Save based on extension
        if path.suffix.lower() in ['.yaml', '.yml']:
            with open(path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        elif path.suffix.lower() == '.json':
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        else:
            raise ValueError(f"Unsupported output format: {path.suffix}. Use .yaml, .yml, or .json")

    @staticmethod
    def load_recipe(recipe_path: str) -> TransferRecipe:
        """
        Load a complete recipe with metadata.

        Parameters:
        ----------
        recipe_path : str
            Path to recipe file

        Returns:
        -------
        TransferRecipe
            Loaded recipe
        """
        path = Path(recipe_path)

        if not path.exists():
            raise FileNotFoundError(f"Recipe file not found: {recipe_path}")

        # Load data
        if path.suffix.lower() in ['.yaml', '.yml']:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
        elif path.suffix.lower() == '.json':
            with open(path, 'r') as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")

        # Create recipe
        return TransferRecipe(
            name=data.get('name', 'Unnamed'),
            description=data.get('description', ''),
            config=data.get('config', {}),
            created_at=data.get('created_at'),
            author=data.get('author'),
            tags=data.get('tags')
        )

    @staticmethod
    def _build_config(config_data: Dict[str, Any]) -> TransferConfig:
        """Build TransferConfig from dictionary."""
        # Parse algorithm
        algorithm_str = config_data.get('algorithm', 'reinhard_lab')
        try:
            algorithm = TransferAlgorithm(algorithm_str)
        except ValueError:
            # Try lowercase
            algorithm = TransferAlgorithm(algorithm_str.lower())

        # Build config
        return TransferConfig(
            algorithm=algorithm,
            blend_factor=float(config_data.get('blend_factor', 1.0)),
            clip_output=bool(config_data.get('clip_output', True)),
            preserve_luminance=bool(config_data.get('preserve_luminance', False)),
            epsilon=float(config_data.get('epsilon', 1e-10))
        )

    @staticmethod
    def get_default_recipes_dir() -> Path:
        """Get default directory for recipes."""
        recipes_dir = Path.home() / '.color_transfer' / 'recipes'
        recipes_dir.mkdir(parents=True, exist_ok=True)
        return recipes_dir

    @staticmethod
    def list_recipes() -> list:
        """List all available recipes."""
        recipes_dir = ConfigLoader.get_default_recipes_dir()
        recipes = []

        for recipe_file in recipes_dir.glob('*.[yj][as][mo][ln]*'):  # Matches .yaml, .yml, .json
            try:
                recipe = ConfigLoader.load_recipe(str(recipe_file))
                recipes.append({
                    'path': str(recipe_file),
                    'name': recipe.name,
                    'description': recipe.description,
                    'tags': recipe.tags
                })
            except Exception as e:
                # Skip invalid recipes
                pass

        return recipes


def create_example_recipes():
    """Create example recipe files for users."""
    recipes_dir = ConfigLoader.get_default_recipes_dir()

    examples = [
        {
            'filename': 'warm_sunset.yaml',
            'recipe': TransferRecipe(
                name="Warm Sunset",
                description="Transfer warm, golden sunset tones",
                config={
                    'algorithm': 'reinhard_lch',
                    'blend_factor': 0.7,
                    'preserve_luminance': True,
                    'clip_output': True
                },
                tags=['warm', 'sunset', 'golden-hour']
            )
        },
        {
            'filename': 'cool_blue.yaml',
            'recipe': TransferRecipe(
                name="Cool Blue",
                description="Transfer cool, blue tones for cinematic look",
                config={
                    'algorithm': 'reinhard_lab',
                    'blend_factor': 0.8,
                    'preserve_luminance': False,
                    'clip_output': True
                },
                tags=['cool', 'blue', 'cinematic']
            )
        },
        {
            'filename': 'high_contrast.yaml',
            'recipe': TransferRecipe(
                name="High Contrast",
                description="Histogram matching for dramatic contrast",
                config={
                    'algorithm': 'histogram_match',
                    'blend_factor': 1.0,
                    'preserve_luminance': False,
                    'clip_output': True
                },
                tags=['contrast', 'dramatic', 'bold']
            )
        },
        {
            'filename': 'subtle_enhancement.yaml',
            'recipe': TransferRecipe(
                name="Subtle Enhancement",
                description="Gentle color correction with low blend",
                config={
                    'algorithm': 'reinhard_lab',
                    'blend_factor': 0.3,
                    'preserve_luminance': True,
                    'clip_output': True
                },
                tags=['subtle', 'gentle', 'correction']
            )
        }
    ]

    for example in examples:
        output_path = recipes_dir / example['filename']
        if not output_path.exists():
            # Create a dummy config for saving
            config = ConfigLoader._build_config(example['recipe'].config)
            ConfigLoader.save_config(config, str(output_path), recipe=example['recipe'])

    print(f"Created {len(examples)} example recipes in {recipes_dir}")
