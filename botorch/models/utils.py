#!/usr/bin/env python3

from copy import deepcopy
from typing import Tuple, Optional

import torch
from gpytorch.module import Module
from gpytorch import fast_pred_var
from torch import Tensor
from botorch.utils import manual_seed


def initialize_BFGP(
        model: Module,
        X: Tensor,
        num_samples: int,
        seed: Optional[int] = None
) -> Module:
    """Initializes a batched fantasized GP from a given GP

    Args:
        model: The input GP model (must not operate in batch mode)
        X: A `k x p` tensor containing the `k` points at which to fantasize
        num_samples: The number of fantasies

    Returns:
        The fantasy model as a GP in batch mode
    """
    # put model in eval mode and save model parameters
    model.eval()
    state_dict = deepcopy(model.state_dict())

    train_targets = model.train_targets
    fantasy_shape: Tuple[int, ...]
    # Includes number of tasks if multi-task GP
    if train_targets.ndimension() > 1:
        fantasy_shape = (num_samples, -1, train_targets.shape[-1])
    else:
        fantasy_shape = (num_samples, -1)
    p = model.train_inputs[0].shape[-1]

    # generate fantasies from model posterior at new q-batch
    posterior = model.likelihood(model(X))
    with manual_seed(seed=seed), fast_pred_var():
        fantasies = posterior.rsample(torch.Size([num_samples]))

    # create new training data tensors
    train_x = torch.cat([model.train_inputs[0], X]).expand(num_samples, -1, p)
    train_y = torch.cat(
        [model.train_targets.expand(*fantasy_shape), fantasies],
        dim=1
    )

    # instantiate the fantasy model(s) and load the (shared) hyperparameters
    likelihood = deepcopy(model.likelihood).eval()
    fantasy_model = model.__class__(train_x, train_y, likelihood)
    fantasy_model.load_state_dict(state_dict)
    fantasy_model.eval()

    return fantasy_model
