#! /usr/bin/env python3

from abc import ABC, abstractmethod
from typing import List, Optional

from torch import Tensor

from ..posteriors import Posterior


class Model(ABC):
    @abstractmethod
    def posterior(
        self,
        X: Tensor,
        output_indices: Optional[List[int]] = None,
        observation_noise: bool = False,
        **kwargs
    ) -> Posterior:
        pass

    def reinitialize(
        self,
        train_X: Tensor,
        train_Y: Tensor,
        train_Y_se: Optional[Tensor] = None,
        keep_params: bool = True,
    ) -> None:
        raise NotImplementedError
