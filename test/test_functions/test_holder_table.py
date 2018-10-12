#! /usr/bin/env python3

import unittest

import torch
from botorch.test_functions.holder_table import (
    GLOBAL_MINIMIZERS,
    GLOBAL_MINIMUM,
    holder_table,
)


class TestHolderTable(unittest.TestCase):
    def test_single_eval_holder_table(self):
        X = torch.zeros(2)
        res = holder_table(X)
        self.assertTrue(res.dtype, torch.float)
        self.assertEqual(res.shape, torch.Size([]))
        self.assertTrue(res.abs().item() < 1e-6)
        res_double = holder_table(X.double())
        self.assertTrue(res_double.dtype, torch.double)
        self.assertEqual(res_double.shape, torch.Size([]))
        self.assertTrue(res_double.abs().item() < 1e-6)

    def test_batch_eval_holder_table(self):
        X = torch.zeros(2, 2)
        res = holder_table(X)
        self.assertTrue(res.dtype, torch.float)
        self.assertEqual(res.shape, torch.Size([2]))
        self.assertTrue(res.abs().sum().item() < 1e-6)
        res_double = holder_table(X.double())
        self.assertTrue(res_double.dtype, torch.double)
        self.assertEqual(res_double.shape, torch.Size([2]))
        self.assertTrue(res_double.abs().sum().item() < 1e-6)

    def test_single_eval_holder_table_cuda(self):
        if torch.cuda.is_available():
            X = torch.zeros(2, device="cuda")
            res = holder_table(X)
            self.assertTrue(res.dtype, torch.float)
            self.assertTrue(res.cuda)
            self.assertEqual(res.shape, torch.Size([]))
            self.assertTrue(res.abs().item() < 1e-6)
            res_double = holder_table(X.double())
            self.assertTrue(res_double.dtype, torch.double)
            self.assertTrue(res_double.cuda)
            self.assertEqual(res_double.shape, torch.Size([]))
            self.assertTrue(res_double.abs().item() < 1e-6)

    def test_batch_eval_holder_table_cuda(self):
        if torch.cuda.is_available():
            X = torch.zeros(2, 2, device="cuda")
            res = holder_table(X)
            self.assertTrue(res.dtype, torch.float)
            self.assertTrue(res.cuda)
            self.assertEqual(res.shape, torch.Size([2]))
            self.assertTrue(res.abs().sum().item() < 1e-6)
            res_double = holder_table(X.double())
            self.assertTrue(res_double.dtype, torch.double)
            self.assertTrue(res_double.cuda)
            self.assertEqual(res_double.shape, torch.Size([2]))
            self.assertTrue(res_double.abs().sum().item() < 1e-6)

    def test_holder_table_gobal_minima(self):
        X = torch.tensor(GLOBAL_MINIMIZERS, requires_grad=True)
        res = holder_table(X)
        torch.autograd.backward([*res])
        self.assertTrue(torch.max((res - GLOBAL_MINIMUM).abs()) < 1e-5)
        self.assertLess(X.grad.abs().max().item(), 1e-3)

    def test_holder_table_gobal_minima_cuda(self):
        if torch.cuda.is_available():
            X = torch.tensor(GLOBAL_MINIMIZERS, device="cuda", requires_grad=True)
            res = holder_table(X)
            torch.autograd.backward([*res])
            self.assertTrue(torch.max((res - GLOBAL_MINIMUM).abs()) < 1e-5)
            self.assertLess(X.grad.abs().max().item(), 1e-3)


if __name__ == "__main__":
    unittest.main()
