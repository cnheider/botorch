#! /usr/bin/env python3

import unittest
from test.utils.mock import MockModel, MockPosterior

import torch
from botorch.acquisition.functional.batch_acquisition import (
    batch_expected_improvement,
    batch_noisy_expected_improvement,
)


class TestFunctionalBatchAcquisition(unittest.TestCase):
    def test_batch_expected_improvement(self, cuda=False):
        device = torch.device("cuda") if cuda else torch.device("cpu")
        for dtype in (torch.float, torch.double):
            samples = torch.zeros([1, 1, 1, 1], device=device, dtype=dtype)
            mm = MockModel(MockPosterior(samples=samples))
            X = torch.zeros(1, device=device, dtype=dtype)  # dummy for type checking
            # basic test
            res = batch_expected_improvement(X=X, model=mm, best_f=0, mc_samples=2)
            self.assertEqual(res.item(), 0)
            # test shifting best_f value
            res2 = batch_expected_improvement(X=X, model=mm, best_f=-1, mc_samples=2)
            self.assertEqual(res2.item(), 1)
            # test modifying the objective
            res3 = batch_expected_improvement(
                X=X,
                model=mm,
                best_f=0,
                objective=lambda Y: torch.ones_like(Y, device=device, dtype=dtype),
                mc_samples=2,
            )
            self.assertEqual(res3.item(), 1)
            # test constraints
            res4 = batch_expected_improvement(
                X=X,
                model=mm,
                best_f=-1,
                constraints=[lambda Y: torch.zeros_like(Y, device=device, dtype=dtype)],
                mc_samples=2,
            )
            self.assertEqual(res4.item(), 0.5)

    def test_batch_expected_improvement_cuda(self):
        if torch.cuda.is_available():
            self.test_batch_expected_improvement(cuda=True)

    def test_batch_noisy_expected_improvement(self, cuda=False):
        device = torch.device("cuda") if cuda else torch.device("cpu")

        for dtype in (torch.float, torch.double):
            samples_noisy = torch.tensor([1.0, 0.0], device=device, dtype=dtype)
            samples_noisy = samples_noisy.view(1, 1, 2, 1)
            X_observed = torch.zeros(1, 1, device=device, dtype=dtype)
            mm_noisy = MockModel(MockPosterior(samples=samples_noisy))

            X = torch.zeros(1, 1, device=device, dtype=dtype)
            # basic test
            res = batch_noisy_expected_improvement(
                X=X, model=mm_noisy, X_observed=X_observed, mc_samples=2
            )
            self.assertEqual(res.item(), 1)
            # test modifying the objective
            res3 = batch_noisy_expected_improvement(
                X=X,
                model=mm_noisy,
                X_observed=X_observed,
                objective=lambda Y: torch.zeros_like(Y, device=device, dtype=dtype),
                mc_samples=2,
            )
            self.assertEqual(res3.item(), 0)
            # test constraints
            res4 = batch_noisy_expected_improvement(
                X=X,
                model=mm_noisy,
                X_observed=X_observed,
                constraints=[lambda Y: torch.zeros_like(Y, device=device, dtype=dtype)],
                mc_samples=2,
            )
            self.assertEqual(res4.item(), 0.5)

        def test_batch_noisy_expected_improvement_cuda(self):
            if torch.cuda.is_available():
                self.test_batch_noisy_expected_improvement(cuda=True)
