"""
Neural Style Transfer
=====================

Deep learning-based color and style transfer using neural networks.

Features:
- VGG-based neural style transfer
- Color transfer in perceptual space
- GPU acceleration support
- Pre-trained model usage
- Fast neural style transfer
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Check for PyTorch availability
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torchvision.models as models
    import torchvision.transforms as transforms
    from torch.autograd import Variable
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. Neural style transfer will use classical fallback.")


class NeuralStyleTransfer:
    """
    Neural style transfer for advanced color and texture transfer.

    Uses VGG19 features for perceptual color transfer when PyTorch is available,
    falls back to classical methods otherwise.

    Example:
        >>> nst = NeuralStyleTransfer(use_gpu=True)
        >>> result = nst.transfer(
        ...     source_image=source,
        ...     target_image=target,
        ...     num_iterations=500
        ... )
    """

    def __init__(self, use_gpu: bool = False, device: str = 'auto'):
        """
        Initialize neural style transfer.

        Parameters:
        -----------
        use_gpu : bool
            Enable GPU acceleration
        device : str
            Device to use ('auto', 'cpu', 'cuda')
        """
        self.use_gpu = use_gpu and TORCH_AVAILABLE

        if device == 'auto':
            if TORCH_AVAILABLE:
                self.device = torch.device('cuda' if torch.cuda.is_available() and use_gpu else 'cpu')
            else:
                self.device = 'cpu'
        else:
            if TORCH_AVAILABLE:
                self.device = torch.device(device)
            else:
                self.device = 'cpu'

        self.model = None
        if TORCH_AVAILABLE and self.use_gpu:
            self._load_vgg_model()

    def _load_vgg_model(self):
        """Load pre-trained VGG19 model."""
        if not TORCH_AVAILABLE:
            return

        try:
            vgg = models.vgg19(pretrained=True).features
            self.model = vgg.to(self.device).eval()

            # Freeze all parameters
            for param in self.model.parameters():
                param.requires_grad_(False)

            logger.info(f"VGG19 model loaded on {self.device}")

        except Exception as e:
            logger.error(f"Failed to load VGG19 model: {e}")
            self.model = None

    def transfer(
        self,
        source_image: np.ndarray,
        target_image: np.ndarray,
        num_iterations: int = 300,
        content_weight: float = 1.0,
        style_weight: float = 1000.0,
        learning_rate: float = 0.01,
        color_only: bool = True
    ) -> np.ndarray:
        """
        Apply neural style transfer.

        Parameters:
        -----------
        source_image : np.ndarray
            Source image (style donor)
        target_image : np.ndarray
            Target image (content)
        num_iterations : int
            Number of optimization iterations
        content_weight : float
            Weight for content loss
        style_weight : float
            Weight for style loss
        learning_rate : float
            Learning rate for optimization
        color_only : bool
            Transfer only color, preserve structure

        Returns:
        --------
        np.ndarray
            Transformed image
        """
        if not TORCH_AVAILABLE or self.model is None:
            logger.warning("Neural style transfer not available, using classical fallback")
            return self._classical_fallback(source_image, target_image)

        try:
            # Prepare images
            source_tensor = self._image_to_tensor(source_image)
            target_tensor = self._image_to_tensor(target_image)

            # Initialize output with target
            output_tensor = target_tensor.clone().requires_grad_(True)

            # Optimizer
            optimizer = optim.Adam([output_tensor], lr=learning_rate)

            # Extract features
            source_features = self._extract_features(source_tensor)
            target_features = self._extract_features(target_tensor)

            # Optimization loop
            for iteration in range(num_iterations):
                optimizer.zero_grad()

                output_features = self._extract_features(output_tensor)

                # Content loss
                content_loss = 0
                if content_weight > 0:
                    content_loss = self._content_loss(
                        output_features,
                        target_features
                    )

                # Style loss (color)
                style_loss = 0
                if style_weight > 0:
                    style_loss = self._style_loss(
                        output_features,
                        source_features
                    )

                # Total loss
                total_loss = content_weight * content_loss + style_weight * style_loss

                # Backprop
                total_loss.backward()
                optimizer.step()

                # Log progress
                if iteration % 50 == 0:
                    logger.info(
                        f"Iteration {iteration}/{num_iterations}: "
                        f"Content Loss: {content_loss:.4f}, "
                        f"Style Loss: {style_loss:.4f}"
                    )

            # Convert back to image
            result = self._tensor_to_image(output_tensor)

            return result

        except Exception as e:
            logger.error(f"Neural style transfer failed: {e}")
            return self._classical_fallback(source_image, target_image)

    def _image_to_tensor(self, image: np.ndarray) -> 'torch.Tensor':
        """Convert numpy image to PyTorch tensor."""
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Normalize to [0, 1]
        image_float = image_rgb.astype(np.float32) / 255.0

        # Convert to tensor [C, H, W]
        tensor = torch.from_numpy(image_float).permute(2, 0, 1).unsqueeze(0)

        return tensor.to(self.device)

    def _tensor_to_image(self, tensor: 'torch.Tensor') -> np.ndarray:
        """Convert PyTorch tensor to numpy image."""
        # Detach and move to CPU
        tensor = tensor.cpu().detach()

        # Remove batch dimension and permute to [H, W, C]
        image = tensor.squeeze(0).permute(1, 2, 0).numpy()

        # Clip to [0, 1] and convert to uint8
        image = np.clip(image, 0, 1)
        image = (image * 255).astype(np.uint8)

        # Convert RGB to BGR
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        return image_bgr

    def _extract_features(self, image_tensor: 'torch.Tensor') -> Dict[str, 'torch.Tensor']:
        """Extract features from VGG19 layers."""
        features = {}

        # Layer indices for feature extraction
        layer_indices = {
            'conv1_1': 0,
            'conv2_1': 5,
            'conv3_1': 10,
            'conv4_1': 19,
            'conv5_1': 28
        }

        x = image_tensor
        for name, module in self.model._modules.items():
            x = module(x)
            if int(name) in layer_indices.values():
                # Find layer name
                for layer_name, idx in layer_indices.items():
                    if int(name) == idx:
                        features[layer_name] = x
                        break

        return features

    def _content_loss(
        self,
        output_features: Dict[str, 'torch.Tensor'],
        target_features: Dict[str, 'torch.Tensor']
    ) -> 'torch.Tensor':
        """Compute content loss."""
        # Use conv4_1 for content
        layer = 'conv4_1'
        return torch.mean((output_features[layer] - target_features[layer]) ** 2)

    def _style_loss(
        self,
        output_features: Dict[str, 'torch.Tensor'],
        source_features: Dict[str, 'torch.Tensor']
    ) -> 'torch.Tensor':
        """Compute style loss using Gram matrices."""
        style_loss = 0

        # Use multiple layers for style
        style_layers = ['conv1_1', 'conv2_1', 'conv3_1', 'conv4_1', 'conv5_1']

        for layer in style_layers:
            output_gram = self._gram_matrix(output_features[layer])
            source_gram = self._gram_matrix(source_features[layer])

            style_loss += torch.mean((output_gram - source_gram) ** 2)

        return style_loss / len(style_layers)

    def _gram_matrix(self, tensor: 'torch.Tensor') -> 'torch.Tensor':
        """Compute Gram matrix for style representation."""
        b, c, h, w = tensor.size()

        # Reshape to [c, h*w]
        features = tensor.view(c, h * w)

        # Compute Gram matrix
        gram = torch.mm(features, features.t())

        # Normalize
        return gram / (c * h * w)

    def _classical_fallback(
        self,
        source: np.ndarray,
        target: np.ndarray
    ) -> np.ndarray:
        """Fallback to classical color transfer when PyTorch unavailable."""
        from ..transfer_engine import TransferEngine, TransferConfig, TransferAlgorithm

        engine = TransferEngine()
        config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

        return engine.transfer(source, target, config)

    def fast_color_transfer(
        self,
        source_image: np.ndarray,
        target_image: np.ndarray
    ) -> np.ndarray:
        """
        Fast neural color transfer using feature matching.

        This is faster than full style transfer but less accurate.
        """
        if not TORCH_AVAILABLE or self.model is None:
            return self._classical_fallback(source_image, target_image)

        try:
            # Extract deep features
            source_tensor = self._image_to_tensor(source_image)
            target_tensor = self._image_to_tensor(target_image)

            source_features = self._extract_features(source_tensor)
            target_features = self._extract_features(target_tensor)

            # Match statistics in feature space
            result_tensor = target_tensor.clone()

            for layer in ['conv1_1', 'conv2_1']:
                source_feat = source_features[layer]
                target_feat = target_features[layer]

                # Match mean and std
                target_mean = target_feat.mean(dim=(2, 3), keepdim=True)
                target_std = target_feat.std(dim=(2, 3), keepdim=True)

                source_mean = source_feat.mean(dim=(2, 3), keepdim=True)
                source_std = source_feat.std(dim=(2, 3), keepdim=True)

                # Normalize and transfer
                normalized = (target_feat - target_mean) / (target_std + 1e-5)
                transferred = normalized * source_std + source_mean

                # Blend back
                result_tensor = 0.7 * result_tensor + 0.3 * transferred

            return self._tensor_to_image(result_tensor)

        except Exception as e:
            logger.error(f"Fast color transfer failed: {e}")
            return self._classical_fallback(source_image, target_image)
