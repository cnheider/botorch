#! /usr/bin/env python3

import unittest

import torch
from botorch.test_functions.hartmann6 import GLOBAL_MINIMIZER, GLOBAL_MINIMUM, hartmann6


class TestHartmann6(unittest.TestCase):
    def test_single_eval_hartmann6(self, cuda=False):
        device = torch.device("cuda") if cuda else torch.device("cpu")
        X = torch.zeros(6, device=device)
        res = hartmann6(X)
        self.assertTrue(res.dtype, torch.float)
        self.assertEqual(res.shape, torch.Size([]))
        res_double = hartmann6(X.double())
        self.assertTrue(res_double.dtype, torch.double)
        self.assertEqual(res_double.shape, torch.Size([]))

    def test_single_eval_hartmann6_cuda(self):
        if torch.cuda.is_available():
            self.test_single_eval_hartmann6(cuda=True)

    def test_batch_eval_hartmann6(self, cuda=False):
        device = torch.device("cuda") if cuda else torch.device("cpu")
        X = torch.zeros(2, 6, device=device)
        res = hartmann6(X)
        self.assertTrue(res.dtype, torch.float)
        self.assertEqual(res.shape, torch.Size([2]))
        res_double = hartmann6(X.double())
        self.assertTrue(res_double.dtype, torch.double)
        self.assertEqual(res_double.shape, torch.Size([2]))

    def test_batch_eval_hartmann6_cuda(self):
        if torch.cuda.is_available():
            self.test_batch_eval_hartmann6(cuda=True)

    def test_hartmann6_gobal_minimum(self, cuda=False):
        device = torch.device("cuda") if cuda else torch.device("cpu")
        X = torch.tensor(GLOBAL_MINIMIZER, device=device, requires_grad=True)
        res = hartmann6(X)
        res.backward()
        self.assertAlmostEqual(res.item(), GLOBAL_MINIMUM, places=4)
        self.assertLess(X.grad.abs().max().item(), 1e-4)

    def test_hartmann6_gobal_minimum_cuda(self):
        if torch.cuda.is_available():
            self.test_hartmann6_gobal_minimum(cuda=False)


if __name__ == "__main__":
    unittest.main()
