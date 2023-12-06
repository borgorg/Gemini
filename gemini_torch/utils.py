import torch
from torch import nn


class ImgToTransformer(nn.Module):
    """ImgToTransformer

    Args:
        patches (int): Number of patches to divide the image into
        patch_size (int): Size of the patches
        transformer_dim (int): Dimension of the transformer
        img_channels (int): Number of channels in the image
        seq_len (int): Length of the sequence
        reduced_dim (int): Dimension of the reduced embedding

    Returns:
        torch.Tensor: The output of the model

    Input shape:
        (batch, channels, height, width)

    Output shape:
        (batch, seq_len, reduced_dim)

    Example:
        >>> import torch
        >>> from geminix import ImgToTransformer
        >>> model = ImgToTransformer(
        ...     patches=16,
        ...     patch_size=16,
        ...     transformer_dim=512,
        ...     img_channels=3,
        ...     seq_len=128,
        ...     reduced_dim=128
        ... )
        >>> x = torch.randn(1, 3, 256, 256)
        >>> y = model(x)
        >>> y.shape
        torch.Size([1, 128, 128])
    """

    def __init__(
        self,
        patches: int,
        patch_size: int,
        transformer_dim: int,
        img_channels: int,
        seq_len: int,
        reduced_dim: int,
        *args,
        **kwargs,
    ):
        super(ImgToTransformer, self).__init__()
        self.patches = patches
        self.patch_size = patch_size
        self.transformer_dim = transformer_dim
        self.img_channels = img_channels
        self.seq_len = seq_len
        self.reduced_dim = reduced_dim

        # Img is a square, cal number of apthces
        self.num_patches_side = int(patches**0.5)

        # Patch embedding layer
        self.patch_embedding = nn.Linear(
            patch_size * patch_size * img_channels, transformer_dim
        )

        # Dim reduction
        self.dim_reduction = nn.Linear(transformer_dim, reduced_dim)

        # Batch Norm and relu
        self.norm = nn.BatchNorm1d(patches)
        self.activate = nn.ReLU()

        # Positional encoding
        self.positional_encoding = nn.Parameter(torch.zeros(1, patches, reduced_dim))

        # Token mixing
        self.token_mixer = nn.Linear(patches * reduced_dim, patches * reduced_dim)

        # Linear layer to expand the seq to vocab
        self.seq_expansion = nn.Linear(patches * reduced_dim, seq_len * reduced_dim)

    def forward(self, x: torch.Tensor):
        batch, channels, height, width, height = x.shape

        # Check if img can be evenly divided into patches
        assert (
            height % self.num_patches_side == 0 and width % self.num_patches_side == 0
        ), f"Image dimensions must be divisivle by the square root of patches"

        # Reshpe the img to patches
        x = x.unfold(
            2,
            self.patch_size,
        ).unfold(3, self.patch_size, self.patch_size)
        x = x.contiguous().view(batch, channels, self.num_patches, -1)
        x = x.permute(0, 2, 1, 3).contiguous().view(batch, self.num_patches, -1)

        # Apply patch embedding
        x = self.patch_embedding(x)

        # Dim reduction
        x = self.dim_reduction(x)

        # Batch norm
        x = self.norm(x)
        x = self.activate(x)

        # Add positional encoding
        x = x.view(batch, -1)
        x = self.token_mixer(x)
        x = x.view(batch, self.num_patches, -1)

        # Expand the seq to match vocab
        x = self.seq_expansion(x)
        x = x.view(batch, self.seq_len, -1)

        return x


# Example usage
num_patches = 16
patch_size = 16
transformer_dim = 512
img_channels = 3
seq_len = 50000
reduced_dim = 256  # Reduced dimension after dimensionality reduction

model = ImgToTransformer(num_patches, patch_size, transformer_dim, img_channels, seq_len, reduced_dim)

# Dummy image input [BATCH, CHANNELS, HEIGHT, WIDTH]
dummy_img = torch.randn(1, 3, 64, 64)  # Batch size of 1, 64x64 RGB image

# Forward pass
seq_space_output = model(dummy_img)
print(seq_space_output.shape)  # Expected shape: [1, 50000, 256]