import torch
import numpy as np

# Configure macOS GPU acceleration (MPS) if available, fallback to CPU
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

class Brain:
    """
    Feedforward Neural Network brain implemented in PyTorch.
    Weights are stored as tensors on the target accelerator device (MPS/CPU).
    Supports genetic crossover and mutation operators.
    """
    def __init__(self, input_size=7, hidden_size=12, output_size=6, weights=None):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        if weights is not None:
            # Clone and ensure tensors are on the correct device
            self.w1 = weights['w1'].clone().to(DEVICE)
            self.w2 = weights['w2'].clone().to(DEVICE)
        else:
            # Initialize random weights in range [-1.0, 1.0] on the device
            self.w1 = (torch.rand((input_size, hidden_size), dtype=torch.float32, device=DEVICE) * 2.0 - 1.0)
            self.w2 = (torch.rand((hidden_size, output_size), dtype=torch.float32, device=DEVICE) * 2.0 - 1.0)

    def feed_forward(self, inputs_list):
        """
        Runs feedforward matrix multiplication through the neural network.
        Accepts a Python list of inputs, converts to a tensor, and performs calculations.
        Returns a dictionary of hidden states and output activations as CPU numpy arrays.
        """
        # Convert input list to PyTorch tensor and move to active acceleration device
        inputs_tensor = torch.tensor(inputs_list, dtype=torch.float32, device=DEVICE)
        
        # Calculate hidden layer: H = tanh(Inputs * W1)
        hidden = torch.tanh(torch.matmul(inputs_tensor, self.w1))
        
        # Calculate output layer: O = tanh(Hidden * W2)
        outputs = torch.tanh(torch.matmul(hidden, self.w2))
        
        # Move back to CPU and convert to numpy array for game loops
        return {
            'hidden': hidden.cpu().numpy(),
            'outputs': outputs.cpu().numpy()
        }

    def mutate(self, rate=0.1):
        """
        Applies a random Gaussian mutation to the weight tensors.
        """
        # Create mutation filters with same shapes
        noise_w1 = torch.normal(mean=0.0, std=0.15, size=self.w1.shape, device=DEVICE)
        mask_w1 = (torch.rand(self.w1.shape, device=DEVICE) < rate).float()
        new_w1 = torch.clamp(self.w1 + noise_w1 * mask_w1, -2.0, 2.0)

        noise_w2 = torch.normal(mean=0.0, std=0.15, size=self.w2.shape, device=DEVICE)
        mask_w2 = (torch.rand(self.w2.shape, device=DEVICE) < rate).float()
        new_w2 = torch.clamp(self.w2 + noise_w2 * mask_w2, -2.0, 2.0)

        return Brain(self.input_size, self.hidden_size, self.output_size, {
            'w1': new_w1,
            'w2': new_w2
        })

    @staticmethod
    def crossover(parent_a, parent_b):
        """
        Performs uniform crossover between two parents, producing a child.
        For each synapse connection weight, there is a 50% chance of inheriting from either parent.
        """
        # Crossover W1
        mask_w1 = torch.rand(parent_a.w1.shape, device=DEVICE) < 0.5
        new_w1 = torch.where(mask_w1, parent_a.w1, parent_b.w1)

        # Crossover W2
        mask_w2 = torch.rand(parent_a.w2.shape, device=DEVICE) < 0.5
        new_w2 = torch.where(mask_w2, parent_a.w2, parent_b.w2)

        return Brain(parent_a.input_size, parent_a.hidden_size, parent_a.output_size, {
            'w1': new_w1,
            'w2': new_w2
        })
