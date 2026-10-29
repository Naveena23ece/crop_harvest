"""
=============================================================================
FILE: training/model_artcn.py
PROJECT: AI-Integrated Predictive Modeling and Adaptive Risk Evaluation DSS
DESCRIPTION:
    Implements the Adaptive Risk-Aware Temporal Convolution Network (AR-TCN).

    Architecture:
      ┌───────────────────────────────────────────────────────────────┐
      │  Input: (batch, seq_len=24, n_features)                       │
      │  ↓                                                            │
      │  Causal Conv1D (expand channels)                              │
      │  ↓                                                            │
      │  ResidualBlock(dilation=1)                                    │
      │  ResidualBlock(dilation=2)                                    │
      │  ResidualBlock(dilation=4)                                    │
      │  ResidualBlock(dilation=8)                                    │
      │  ResidualBlock(dilation=16)                                   │
      │  ↓                                                            │
      │  Global Average Pooling (temporal dim)                        │
      │  ↓                                                            │
      │  Adaptive Risk Head: Dense(128) → BN → ReLU → Dropout        │
      │  Dense(64) → BN → ReLU → Dropout                             │
      │  Dense(3) → Softmax                                           │
      └───────────────────────────────────────────────────────────────┘

    Key design choices:
      - Dilated convolutions capture multi-scale temporal patterns
      - Residual connections prevent vanishing gradients
      - Causal padding ensures no future data leakage
      - Batch normalisation stabilises training
      - "Adaptive" refers to the configurable dilation schedule and
        the risk-weighted head architecture
=============================================================================
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List


# ─────────────────────────────────────────────
# CAUSAL CONVOLUTION BLOCK
# ─────────────────────────────────────────────
class CausalConv1d(nn.Module):
    """
    1-D convolution with causal (left-only) padding.
    Ensures the model never sees future timesteps.
    """
    def __init__(self, in_channels: int, out_channels: int,
                 kernel_size: int, dilation: int = 1):
        super().__init__()
        # Left-pad so output length = input length
        self.padding = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(
            in_channels, out_channels, kernel_size,
            dilation=dilation, padding=0, bias=False
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, channels, time)
        x = F.pad(x, (self.padding, 0))
        return self.conv(x)


# ─────────────────────────────────────────────
# RESIDUAL BLOCK (core AR-TCN building unit)
# ─────────────────────────────────────────────
class ResidualBlock(nn.Module):
    """
    Dilated residual block with two causal convolutions.
    Structure per block:
        CausalConv → BN → ReLU → Dropout
        CausalConv → BN → ReLU → Dropout
        + skip connection (1×1 conv if channels differ)
    """
    def __init__(self, in_channels: int, out_channels: int,
                 kernel_size: int = 3, dilation: int = 1,
                 dropout: float = 0.2):
        super().__init__()
        self.conv1 = CausalConv1d(in_channels,  out_channels, kernel_size, dilation)
        self.bn1   = nn.BatchNorm1d(out_channels)
        self.conv2 = CausalConv1d(out_channels, out_channels, kernel_size, dilation)
        self.bn2   = nn.BatchNorm1d(out_channels)
        self.drop  = nn.Dropout(dropout)

        # 1×1 skip connection if channel dimensions differ
        self.skip = (
            nn.Conv1d(in_channels, out_channels, kernel_size=1, bias=False)
            if in_channels != out_channels else nn.Identity()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.skip(x)

        out = self.drop(F.relu(self.bn1(self.conv1(x))))
        out = self.drop(F.relu(self.bn2(self.conv2(out))))

        # Residual addition
        out = out + residual
        return F.relu(out)


# ─────────────────────────────────────────────
# AR-TCN MODEL
# ─────────────────────────────────────────────
class ARTCN(nn.Module):
    """
    Adaptive Risk-Aware Temporal Convolution Network.

    Args:
        n_features:    Number of input features per timestep
        n_classes:     Number of output classes (3: Low/Moderate/High)
        seq_len:       Input sequence length (default 24)
        base_channels: Initial number of convolutional channels
        dilations:     List of dilation factors for residual blocks
        kernel_size:   Convolution kernel size
        dropout:       Dropout rate
    """
    def __init__(
        self,
        n_features:    int,
        n_classes:     int   = 3,
        seq_len:       int   = 24,
        base_channels: int   = 64,
        dilations:     List  = [1, 2, 4, 8, 16],
        kernel_size:   int   = 3,
        dropout:       float = 0.25,
    ):
        super().__init__()
        self.n_features    = n_features
        self.n_classes     = n_classes
        self.seq_len       = seq_len

        # ── Input projection ──────────────────
        # Project raw n_features → base_channels
        self.input_proj = nn.Sequential(
            CausalConv1d(n_features, base_channels, kernel_size=1),
            nn.BatchNorm1d(base_channels),
            nn.ReLU(),
        )

        # ── Stacked residual blocks ───────────
        blocks = []
        in_ch  = base_channels
        for i, dil in enumerate(dilations):
            # Double channels at certain depths for richer representation
            out_ch = base_channels * (2 if i >= len(dilations) // 2 else 1)
            blocks.append(
                ResidualBlock(in_ch, out_ch, kernel_size, dil, dropout)
            )
            in_ch = out_ch
        self.tcn_blocks = nn.Sequential(*blocks)
        self.final_channels = in_ch

        # ── Global Average Pooling ────────────
        # Collapses temporal dimension → (batch, channels)
        self.gap = nn.AdaptiveAvgPool1d(1)

        # ── Risk head (classification) ────────
        self.risk_head = nn.Sequential(
            nn.Linear(self.final_channels, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, n_classes),
        )

        # Weight initialisation
        self._init_weights()

    def _init_weights(self):
        """Kaiming initialisation for conv layers; Xavier for linear."""
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, n_features)
        Returns:
            logits: (batch, n_classes)
        """
        # PyTorch Conv1d expects (batch, channels, time)
        x = x.permute(0, 2, 1)          # → (B, F, T)

        x = self.input_proj(x)           # → (B, C, T)
        x = self.tcn_blocks(x)           # → (B, C', T)

        x = self.gap(x)                  # → (B, C', 1)
        x = x.squeeze(-1)                # → (B, C')

        logits = self.risk_head(x)       # → (B, n_classes)
        return logits

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Returns softmax probabilities."""
        return F.softmax(self.forward(x), dim=-1)

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ─────────────────────────────────────────────
# FACTORY FUNCTION
# ─────────────────────────────────────────────
def build_artcn(n_features: int, n_classes: int = 3, **kwargs) -> ARTCN:
    """Creates and returns an AR-TCN model instance."""
    model = ARTCN(n_features=n_features, n_classes=n_classes, **kwargs)
    print(f"[AR-TCN] Built model with {model.count_parameters():,} trainable parameters")
    return model


if __name__ == "__main__":
    # Quick architecture verification
    B, T, F = 4, 24, 60   # batch=4, seq_len=24, features=60
    model  = build_artcn(n_features=F, n_classes=3)
    dummy  = torch.randn(B, T, F)
    out    = model(dummy)
    print(f"Input:  {dummy.shape}")
    print(f"Output: {out.shape}")   # (4, 3)
    print(f"Params: {model.count_parameters():,}")
