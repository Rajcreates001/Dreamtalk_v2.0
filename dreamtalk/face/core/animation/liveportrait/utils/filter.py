# Dreamtalk - Face Engine
# Extracted from LivePortrait
import torch


def smooth(x, shape, device, observation_variance=3e-7):
    """Apply Kalman-like smoothing to a sequence of tensors."""
    if isinstance(x, list) and len(x) > 0:
        if isinstance(x[0], np.ndarray):
            x_tensor = torch.from_numpy(np.stack(x)).to(device)
        else:
            x_tensor = torch.stack(x).to(device)

        if x_tensor.ndim == 2:
            x_tensor = x_tensor.unsqueeze(0)

        smoothed = []
        for b in range(x_tensor.shape[0]):
            seq = x_tensor[b]
            state = seq[0].clone()
            for i in range(len(seq)):
                # Simple exponentially weighted smoothing
                alpha = 1.0 / (1.0 + observation_variance)
                state = alpha * seq[i] + (1 - alpha) * state
                smoothed.append(state.clone())
            smoothed = torch.stack(smoothed)
        return smoothed
    return x
