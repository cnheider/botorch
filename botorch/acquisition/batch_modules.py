#!/usr/bin/env python3

from typing import Callable, List, Optional

import torch

from ..models.model import Model
from ..models.utils import initialize_batch_fantasy_GP
from .batch_utils import construct_base_samples_from_posterior, match_batch_size
from .functional.batch_acquisition import (
    batch_expected_improvement,
    batch_knowledge_gradient,
    batch_noisy_expected_improvement,
    batch_probability_of_improvement,
    batch_simple_regret,
    batch_upper_confidence_bound,
)
from .modules import AcquisitionFunction


"""
Wraps the batch acquisition functions defined in botorch.acquisition.functional
into BatchAcquisitionFunction gpytorch modules.
"""


class BatchAcquisitionFunction(AcquisitionFunction):
    def __init__(
        self,
        model: Model,
        mc_samples: int = 5000,
        X_pending: Optional[torch.Tensor] = None,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(model=model)
        self.mc_samples = mc_samples
        self.X_pending = X_pending
        if self.X_pending is not None:
            self.X_pending.requires_grad_(False)
        self.seed = seed
        self.base_samples = None
        self.base_samples_q_batch_size = None

    def _forward(self, X: torch.Tensor) -> torch.Tensor:
        """Takes in a `b x q x d` X Tensor of `b` t-batches with `q`
        `d`-dimensional design points each, and returns a one-dimensional Tensor
        with `b` elements."""
        raise NotImplementedError("BatchAcquisitionFunction cannot be used directly")

    def forward(self, X: torch.Tensor) -> torch.Tensor:
        """Takes in a `b x q x d` X Tensor of `b` t-batches with `q`
        `d`-dimensional design points each, expands and concatenates self.X_pending
        and returns a one-dimensional Tensor with `b` elements."""
        if self.X_pending is not None:
            X = torch.cat([X, match_batch_size(X, self.X_pending)], dim=-2)
        if self.seed is not None:
            if self.base_samples_q_batch_size != X.shape[-2]:
                # Remove batch dimension for base sample construction.
                # We rely upon the @batch_mode_transform decorator
                # to expand base_samples to the appropriate batch size within
                # a call to batch_acquisition.
                self._construct_base_samples(X if X.dim() < 3 else X[0, ...])
                self.base_samples_q_batch_size = X.shape[-2]
        return self._forward(X)

    def _construct_base_samples(self, X: torch.Tensor) -> None:
        posterior = self.model.posterior(X)
        self.base_samples = construct_base_samples_from_posterior(
            posterior=posterior, num_samples=self.mc_samples, seed=self.seed
        )


class qExpectedImprovement(BatchAcquisitionFunction):
    """q-EI with constraints, supporting t-batch mode.

    Args:
        model: A fitted model.
        best_f: The best (feasible) function value observed so far (assumed
            noiseless).
        objective: A callable mapping a Tensor of size `b x q x (t)` to a Tensor
            of size `b x q`, where `t` is the number of outputs (tasks) of the model.
            Note: the callable must support broadcasting.
            If omitted, use the identity map (applicable to single-task models only).
            Assumed to be non-negative when the constraints are used!
        constraints: A list of callables, each mapping a Tensor of size `b x q x t`
            to a Tensor of size `b x q`, where negative values imply feasibility.
            Note: the callable must support broadcasting.
            Only relevant for multi-task models (`t` > 1).
        mc_samples: The number of Monte-Carlo samples to draw from the model
            posterior.
        X_pending:  A `q' x d` Tensor with `q'` design points that are pending for
            evaluation.
        seed: If seed is provided, do deterministic optimization where the
            function to optimize is fixed and not stochastic.
    """

    def __init__(
        self,
        model: Model,
        best_f: float,
        objective: Callable[[torch.Tensor], torch.Tensor] = lambda Y: Y,
        constraints: Optional[List[Callable[[torch.Tensor], torch.Tensor]]] = None,
        mc_samples: int = 5000,
        X_pending: Optional[torch.Tensor] = None,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(
            model=model, mc_samples=mc_samples, X_pending=X_pending, seed=seed
        )
        self.best_f = best_f
        self.objective = objective
        self.constraints = constraints

    def _forward(self, X: torch.Tensor) -> torch.Tensor:
        """
        Args:
            X: A `b x q x d` Tensor with `b` t-batches of `q` design points
                each. If X is two-dimensional, assume `b = 1`.

        Returns:
            Tensor: The constrained q-EI value of the design X for each of the `b`
                t-batches.
        """
        return batch_expected_improvement(
            X=X,
            model=self.model,
            best_f=self.best_f,
            objective=self.objective,
            constraints=self.constraints,
            mc_samples=self.mc_samples,
            base_samples=self.base_samples,
        )


class qNoisyExpectedImprovement(BatchAcquisitionFunction):
    """q-NoisyEI with constraints, supporting t-batch mode.

    Args:
        model: A fitted model.
        X_observed: A q' x d Tensor of q' design points that have already been
            observed and would be considered as the best design point.
        objective: A callable mapping a Tensor of size `b x q x (t)`
            to a Tensor of size `b x q`, where `t` is the number of
            outputs (tasks) of the model. Note: the callable must support broadcasting.
            If omitted, use the identity map (applicable to single-task models only).
            Assumed to be non-negative when the constraints are used!
        constraints: A list of callables, each mapping a Tensor of size
            `b x q x t` to a Tensor of size `b x q`, where negative values imply
            feasibility. Note: the callable must support broadcasting. Only
            relevant for multi-task models (`t` > 1).
        mc_samples: The number of Monte-Carlo samples to draw from the model
            posterior.
        eta: The temperature parameter of the softmax function used in approximating
            the constraints. As `eta -> 0`, the exact (discontinuous) constraint
            is recovered.
        X_pending:  A q' x d Tensor with q' design points that are pending for
            evaluation.
        seed: If seed is provided, do deterministic optimization where the
            function to optimize is fixed and not stochastic.

    """

    def __init__(
        self,
        model: Model,
        X_observed: torch.Tensor,
        objective: Callable[[torch.Tensor], torch.Tensor] = lambda Y: Y,
        constraints: Optional[List[Callable[[torch.Tensor], torch.Tensor]]] = None,
        mc_samples: int = 5000,
        X_pending: Optional[torch.Tensor] = None,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(
            model=model, mc_samples=mc_samples, X_pending=X_pending, seed=seed
        )
        # TODO: get X_observed from model?
        self.X_observed = X_observed
        self.objective = objective
        self.constraints = constraints

    def _construct_base_samples(self, X: torch.Tensor) -> None:
        X_all = torch.cat([X, self.X_observed], dim=-2)
        posterior = self.model.posterior(X_all)
        self.base_samples = construct_base_samples_from_posterior(
            posterior=posterior, num_samples=self.mc_samples, seed=self.seed
        )
        return

    def _forward(self, X: torch.Tensor) -> torch.Tensor:
        """
        Args:
            X: A `b x q x d` Tensor with `b` t-batches of `q` design points each.
                If X is two-dimensional, assume `b = 1`.

        Returns:
            Tensor: The constrained q-NoisyEI value of the design X for each of the `b`
                t-batches.

        """
        return batch_noisy_expected_improvement(
            X=X,
            model=self.model,
            X_observed=self.X_observed,
            objective=self.objective,
            constraints=self.constraints,
            mc_samples=self.mc_samples,
            base_samples=self.base_samples,
        )


class qKnowledgeGradient(BatchAcquisitionFunction):
    """Constrained, multi-fidelity q-KG (q-knowledge gradient).

    This function supports t-batches in an inefficient manner.

    Multifidelity optimization can be performed by using the
    optional project and cost callables.

    Args:
        model: A fitted GPyTorchModel (required to efficiently generate fantasies)
        X_observed: A q' x d Tensor of q' design points that have already been
            observed and would be considered as the best design point.  A
            judicious filtering of the points here can massively
            speed up the function evaluation without altering the
            function if points that are highly unlikely to be the
            best (regardless of what is observed at X) are removed.
            For example, points that clearly do not satisfy the constraints
            or have terrible objective observations can be safely
            excluded from X_observed.
        objective: A callable mapping a Tensor of size `b x q x (t)`
            to a Tensor of size `b x q`, where `t` is the number of
            outputs (tasks) of the model. Note: the callable must support broadcasting.
            If omitted, use the identity map (applicable to single-task models only).
            Assumed to be non-negative when the constraints are used!
        constraints: A list of callables, each mapping a Tensor of size
            `b x q x t` to a Tensor of size `b x q`, where negative values imply
            feasibility. Note: the callable must support broadcasting. Only
            relevant for multi-task models (`t` > 1).
        mc_samples: The number of Monte-Carlo samples to draw from the model
            posterior for the outer sample.  GP memory usage is multiplied by
            this value.
        inner_mc_samples:  The number of Monte-Carlo samples to draw for the
            inner expectation
        project:  A callable mapping a Tensor of size `b x (q + q') x d` to a
            Tensor of the same size.  Use for multi-fidelity optimization where
            the returned Tensor should be projected to the highest fidelity.
        cost: A callable mapping a Tensor of size `b x q x d` to a Tensor of
            size `b x 1`.  The resulting Tensor's value is the cost of submitting
            each t-batch.
        X_pending: A q' x d Tensor with q' design points that are pending for
            evaluation.
        seed: If seed is provided, do deterministic optimization where the
            function to optimize is fixed and not stochastic.

    Returns:
        Tensor: The q-KG value of the design X for each of the `b`
            t-batches.

    """

    def __init__(
        self,
        model: Model,
        X_observed: torch.Tensor,
        objective: Callable[[torch.Tensor], torch.Tensor] = lambda Y: Y,
        constraints: Optional[List[Callable[[torch.Tensor], torch.Tensor]]] = None,
        mc_samples: int = 40,
        inner_mc_samples: int = 1000,
        project: Callable[[torch.Tensor], torch.Tensor] = lambda X: X,
        cost: Optional[Callable[[torch.Tensor], torch.Tensor]] = None,
        X_pending: Optional[torch.Tensor] = None,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(
            model=model, mc_samples=mc_samples, X_pending=X_pending, seed=seed
        )
        self.X_observed = X_observed
        self.objective = objective
        self.constraints = constraints
        self.inner_mc_samples = inner_mc_samples
        self.project = project
        self.cost = cost

        self.inner_old_base_samples = None
        self.inner_new_base_samples = None
        self.fantasy_base_samples = None

    def _construct_base_samples(self, X: torch.Tensor) -> None:
        # TODO: remove [0] in base_samples when qKG works with t-batches
        old_posterior = self.model.posterior(self.X_observed)
        self.inner_old_base_samples = construct_base_samples_from_posterior(
            posterior=old_posterior, num_samples=self.inner_mc_samples, seed=self.seed
        )[0]

        posterior = self.model(X)
        self.fantasy_base_samples = construct_base_samples_from_posterior(
            posterior=posterior, num_samples=self.mc_samples, seed=self.seed
        )[0]

        X_all = torch.cat([X, self.X_observed], dim=-2)
        fantasy_model = initialize_batch_fantasy_GP(
            model=self.model, X=X, num_samples=self.mc_samples
        )
        new_posterior = fantasy_model.posterior(
            X_all.unsqueeze(0).repeat(self.mc_samples, 1, 1)
        )
        self.inner_new_base_samples = construct_base_samples_from_posterior(
            posterior=new_posterior, num_samples=self.inner_mc_samples, seed=self.seed
        )[0]

    def _forward(self, X: torch.Tensor) -> torch.Tensor:
        """
        Args:
            X: A `b x q x d` Tensor with `b` t-batches of `q` design points each.
                If X is two-dimensional, assume `b = 1`.

        Returns:
            Tensor: The constrained q-KG value of the design X for each of the `b`
                t-batches.

        """
        # TODO: update this when batch_knowledge_gradient supports t-batches
        Xs = list(X) if X.dim() > 2 else [X]
        return torch.cat(
            [
                batch_knowledge_gradient(
                    X=Xi,
                    model=self.model,
                    X_observed=self.X_observed,
                    objective=self.objective,
                    constraints=self.constraints,
                    mc_samples=self.mc_samples,
                    inner_mc_samples=self.inner_mc_samples,
                    inner_old_base_samples=self.inner_old_base_samples,
                    inner_new_base_samples=self.inner_new_base_samples,
                    fantasy_base_samples=self.fantasy_base_samples,
                    project=self.project,
                    cost=self.cost,
                ).reshape(1)
                for Xi in Xs
            ]
        )


class qProbabilityOfImprovement(BatchAcquisitionFunction):
    """q-PI, supporting t-batch mode.

    Args:
        X: A `b x q x d` Tensor with `b` t-batches of `q` design points
            each. If X is two-dimensional, assume `b = 1`.
        model: A fitted model.
        best_f: The best (feasible) function value observed so far (assumed
            noiseless).
        mc_samples: The number of Monte-Carlo samples to draw from the model
            posterior.
        X_pending:  A q' x d Tensor with q' design points that are pending for
            evaluation.
        seed: If seed is provided, do deterministic optimization where the
            function to optimize is fixed and not stochastic.

    """

    def __init__(
        self,
        model: Model,
        best_f: float,
        mc_samples: int = 5000,
        X_pending: Optional[torch.Tensor] = None,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(
            model=model, mc_samples=mc_samples, X_pending=X_pending, seed=seed
        )
        self.best_f = best_f

    def _forward(self, X: torch.Tensor) -> torch.Tensor:
        """
        Args:
            X: A `b x q x d` Tensor with `b` t-batches of `q` design points
                each. If X is two-dimensional, assume `b = 1`.

        Returns:
            Tensor: The constrained q-PI value of the design X for each of the `b`
                t-batches.

        """
        return batch_probability_of_improvement(
            X=X,
            model=self.model,
            best_f=self.best_f,
            mc_samples=self.mc_samples,
            base_samples=self.base_samples,
        )


class qUpperConfidenceBound(BatchAcquisitionFunction):
    """q-UCB, supporting t-batch mode.

    Args:
        X: A `b x q x d` Tensor with `b` t-batches of `q` design points
            each. If X is two-dimensional, assume `b = 1`.
        model: A fitted model.
        beta: controls tradeoff between mean and standard deviation in UCB
        mc_samples: The number of Monte-Carlo samples to draw from the model
            posterior.
        X_pending:  A q' x d Tensor with q' design points that are pending for
            evaluation.
        seed: If seed is provided, do deterministic optimization where the
            function to optimize is fixed and not stochastic.

    Returns:
        Tensor: The constrained q-UCB value of the design X for each of
            the `b`t-batches.

    """

    def __init__(
        self,
        model: Model,
        beta: float,
        mc_samples: int = 5000,
        X_pending: Optional[torch.Tensor] = None,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(
            model=model, mc_samples=mc_samples, X_pending=X_pending, seed=seed
        )
        self.beta = beta

    def _forward(self, X: torch.Tensor) -> torch.Tensor:
        """
        Args:
            X: A `b x q x d` Tensor with `b` t-batches of `q` design points
                each. If X is two-dimensional, assume `b = 1`.

        Returns:
            Tensor: The constrained q-UCB value of the design X for each of
                the `b`t-batches.

        """
        return batch_upper_confidence_bound(
            X=X,
            model=self.model,
            beta=self.beta,
            mc_samples=self.mc_samples,
            seed=self.seed,
        )


class qSimpleRegret(BatchAcquisitionFunction):
    """q-simple regret, supporting t-batch mode.

    Args:
        model: A fitted model.
        mc_samples: The number of Monte-Carlo samples to draw from the model
            posterior.
        X_pending:  A q' x d Tensor with q' design points that are pending for
            evaluation.
        seed: If seed is provided, do deterministic optimization where the
            function to optimize is fixed and not stochastic.

    """

    def __init__(
        self,
        model: Model,
        mc_samples: int = 5000,
        X_pending: Optional[torch.Tensor] = None,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(
            model=model, mc_samples=mc_samples, X_pending=X_pending, seed=seed
        )

    def _forward(self, X: torch.Tensor) -> torch.Tensor:
        """
        Args:
            X: A `b x q x d` Tensor with `b` t-batches of `q` design points
                each. If X is two-dimensional, assume `b = 1`.

        Returns:
            Tensor: The constrained q-simple regret value of the design X for each of
                the `b`t-batches.

        """
        return batch_simple_regret(
            X=X,
            model=self.model,
            mc_samples=self.mc_samples,
            base_samples=self.base_samples,
        )
