#! /usr/bin/env python3

import unittest

import torch
from botorch.utils import (
    check_convergence,
    columnwise_clamp,
    fix_features,
    gen_x_uniform,
    get_objective_weights_transform,
    manual_seed,
    standardize,
)


class TestCheckConvergence(unittest.TestCase):
    def test_check_convergence(self, cuda=False):
        losses = torch.rand(5).tolist()
        self.assertTrue(
            check_convergence(
                loss_trajectory=losses, param_trajectory=[], options={"maxiter": 5}
            )
        )
        self.assertFalse(
            check_convergence(
                loss_trajectory=losses, param_trajectory=[], options={"maxiter": 6}
            )
        )

    def test_check_convergence_cuda(self):
        if torch.cuda.is_available():
            self.test_check_convergence(cuda=True)


class TestFixFeatures(unittest.TestCase):
    def _getTensors(self, device):
        X = torch.tensor([[-2, 1, 3], [0.5, -0.5, 1.0]], device=device)
        X_null_two = torch.tensor([[-2, 1, 3], [0.5, -0.5, 1.0]], device=device)
        X_expected = torch.tensor([[-1, 1, -2], [-1, -0.5, -2]], device=device)
        X_expected_null_two = torch.tensor([[-1, 1, 3], [-1, -0.5, 1.0]], device=device)
        return X, X_null_two, X_expected, X_expected_null_two

    def test_fix_features(self, cuda=False):
        device = torch.device("cuda") if cuda else torch.device("cpu")
        X, X_null_two, X_expected, X_expected_null_two = self._getTensors(device)
        X.requires_grad_(True)
        X_null_two.requires_grad_(True)

        X_fix = fix_features(X, {0: -1, 2: -2})
        X_fix_null_two = fix_features(X_null_two, {0: -1, 2: None})

        self.assertTrue(torch.equal(X_fix, X_expected))
        self.assertTrue(torch.equal(X_fix_null_two, X_expected_null_two))

        def f(X):
            return X.sum()

        f(X).backward()
        self.assertTrue(torch.equal(X.grad, torch.ones_like(X)))
        X.grad.zero_()

        f(X_fix).backward()
        self.assertTrue(
            torch.equal(
                X.grad, torch.tensor([[0.0, 1.0, 0.0], [0.0, 1.0, 0.0]], device=device)
            )
        )

        f(X_null_two).backward()
        self.assertTrue(torch.equal(X_null_two.grad, torch.ones_like(X)))
        X_null_two.grad.zero_()
        f(X_fix_null_two).backward()
        self.assertTrue(
            torch.equal(
                X_null_two.grad,
                torch.tensor([[0.0, 1.0, 0.0], [0.0, 1.0, 0.0]], device=device),
            )
        )

    def test_fix_features_cuda(self):
        if torch.cuda.is_available():
            self.test_fix_features(cuda=True)


class TestColumnWiseClamp(unittest.TestCase):
    def setUp(self):
        self.X = torch.tensor([[-2, 1], [0.5, -0.5]])
        self.X_expected = torch.tensor([[-1, 0.5], [0.5, -0.5]])

    def test_column_wise_clamp_scalars(self, cuda=False):
        X = self.X.cuda() if cuda else self.X
        X_expected = self.X_expected.cuda() if cuda else self.X_expected
        with self.assertRaises(ValueError):
            X_clmp = columnwise_clamp(X, 1, -1)
        X_clmp = columnwise_clamp(X, -1, 0.5)
        self.assertTrue(torch.equal(X_clmp, X_expected))
        X_clmp = columnwise_clamp(X, -3, 3)
        self.assertTrue(torch.equal(X_clmp, X))

    def test_column_wise_clamp_scalars_cuda(self):
        if torch.cuda.is_available():
            self.test_column_wise_clamp_scalars(cuda=True)

    def test_column_wise_clamp_scalar_tensors(self, cuda=False):
        X = self.X.cuda() if cuda else self.X
        X_expected = self.X_expected.cuda() if cuda else self.X_expected
        with self.assertRaises(ValueError):
            X_clmp = columnwise_clamp(X, torch.tensor(1), torch.tensor(-1))
        X_clmp = columnwise_clamp(X, torch.tensor(-1), torch.tensor(0.5))
        self.assertTrue(torch.equal(X_clmp, X_expected))
        X_clmp = columnwise_clamp(X, torch.tensor(-3), torch.tensor(3))
        self.assertTrue(torch.equal(X_clmp, X))

    def test_column_wise_clamp_scalar_tensors_cuda(self):
        if torch.cuda.is_available():
            self.test_column_wise_clamp_scalar_tensors(cuda=True)

    def test_column_wise_clamp_tensors(self, cuda=False):
        X = self.X.cuda() if cuda else self.X
        X_expected = self.X_expected.cuda() if cuda else self.X_expected
        with self.assertRaises(ValueError):
            X_clmp = columnwise_clamp(X, torch.ones(2), torch.zeros(2))
        with self.assertRaises(RuntimeError):
            X_clmp = columnwise_clamp(X, torch.zeros(3), torch.ones(3))
        X_clmp = columnwise_clamp(X, torch.tensor([-1, -1]), torch.tensor([0.5, 0.5]))
        self.assertTrue(torch.equal(X_clmp, X_expected))
        X_clmp = columnwise_clamp(X, torch.tensor([-3, -3]), torch.tensor([3, 3]))
        self.assertTrue(torch.equal(X_clmp, X))

    def test_column_wise_clamp_tensors_cuda(self):
        if torch.cuda.is_available():
            self.test_column_wise_clamp_tensors(cuda=True)


class TestManualSeed(unittest.TestCase):
    def test_manual_seed(self):
        initial_state = torch.random.get_rng_state()
        with manual_seed():
            self.assertTrue(torch.all(torch.random.get_rng_state() == initial_state))
        with manual_seed(1234):
            self.assertFalse(torch.all(torch.random.get_rng_state() == initial_state))
        self.assertTrue(torch.all(torch.random.get_rng_state() == initial_state))


class TestGenXUniform(unittest.TestCase):
    def setUp(self):
        self.bounds = torch.tensor([[0.0, 1.0, 2.0, 3.0], [1.0, 4.0, 5.0, 7.0]])
        self.d = self.bounds.shape[-1]

    def testGenXUniform(self, cuda=False):
        device = torch.device("cuda") if cuda else torch.device("cpu")
        for dtype in (torch.float, torch.double):
            bnds = self.bounds.to(dtype=dtype, device=device)
            X = gen_x_uniform(2, 3, bnds)
            self.assertTrue(X.shape == torch.Size([2, 3, self.d]))
            X_flat = X.view(-1, self.d)
            self.assertTrue(torch.all(X_flat.max(0)[0] <= bnds[1]))
            self.assertTrue(torch.all(X_flat.min(0)[0] >= bnds[0]))

    def testGenXUniform_cuda(self):
        if torch.cuda.is_available():
            self.testGenXUniform(cuda=True)


class TestGetObjectiveWeightsTransform(unittest.TestCase):
    def setUp(self):
        self.b = 2
        self.q = 4
        self.mc_samples = 5

    def testNoWeights(self):
        X = torch.ones((self.mc_samples, self.b, self.q), dtype=torch.float32)
        objective_transform = get_objective_weights_transform(None)
        X_transformed = objective_transform(X)
        self.assertTrue(torch.equal(X, X_transformed))
        objective_transform = get_objective_weights_transform(torch.tensor([]))
        X_transformed = objective_transform(X)
        self.assertTrue(torch.equal(X, X_transformed))

    def testOneWeight(self):
        X = torch.ones((self.mc_samples, self.b, self.q))
        objective_transform = get_objective_weights_transform(torch.tensor([-1.0]))
        X_transformed = objective_transform(X)
        self.assertTrue(torch.equal(X, -1 * X_transformed))

    def testMultiTaskWeights(self):
        X = torch.ones((self.mc_samples, self.b, self.q, 2))
        objective_transform = get_objective_weights_transform(torch.tensor([1.0, 1.0]))
        X_transformed = objective_transform(X)
        self.assertTrue(torch.equal(torch.sum(X, dim=-1), X_transformed))

    def testNoMCSamples(self):
        X = torch.ones((self.b, self.q, 2))
        objective_transform = get_objective_weights_transform(torch.tensor([1.0, 1.0]))
        X_transformed = objective_transform(X)
        self.assertTrue(torch.equal(torch.sum(X, dim=-1), X_transformed))


class TestStandardize(unittest.TestCase):
    def test_standardize(self):
        X = torch.tensor([0.0, 0.0])
        self.assertTrue(torch.equal(X, standardize(X)))
        X2 = torch.tensor([0.0, 1.0, 1.0, 1.0])
        expected_X2_stdized = torch.tensor([-1.5, 0.5, 0.5, 0.5])
        self.assertTrue(torch.equal(expected_X2_stdized, standardize(X2)))
        X3 = torch.tensor([[0.0, 1.0, 1.0, 1.0], [0.0, 0.0, 0.0, 0.0]]).transpose(1, 0)
        X3_stdized = standardize(X3)
        self.assertTrue(torch.equal(X3_stdized[:, 0], expected_X2_stdized))
        self.assertTrue(torch.equal(X3_stdized[:, 1], torch.zeros(4)))


if __name__ == "__main__":
    unittest.main()
