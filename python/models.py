#!/usr/bin/env python
# -*- coding: utf-8 -*-



# Imports.
import numpy                                as np
import os
import sys
import torch
import torch                                as T
import torch.autograd                       as TA
import torch.cuda                           as TC
import torch.nn                             as TN
import torch.optim                          as TO
import torch.utils                          as TU
import torch.utils.data                     as TUD

from   torch.nn     import (Conv2d, BatchNorm2d, MaxPool2d, AvgPool2d, ReLU,
                            CrossEntropyLoss, Linear)

from   functional                           import *
from   layers                               import *



#
# For the sake of ease of use, all models below inherit from this class, which
# exposes a constrain() method that allows re-applying the module's constraints
# to its parameters.
#
class ModelConstrained(torch.nn.Module):
	def constrain(self):
		def fn(module):
			if module is not self and hasattr(module, "constrain"):
				module.constrain()
		
		self.apply(fn)


#
# Real-valued model
#

class RealModel(TN.Module):
	def __init__(self, d):
		super(RealModel, self).__init__()
		self.d      = d
		self.conv0  = TN.Conv2d          (  1 if self.d.dataset == "mnist" else 3,
		                                        64, (3,3), padding=1)
		self.bn0    = TN.BatchNorm2d     ( 64,  affine=False)
		self.relu0  = TN.ReLU            ()
		self.conv1  = TN.Conv2d          ( 64,  64, (3,3), padding=1)
		self.bn1    = TN.BatchNorm2d     ( 64,  affine=False)
		self.relu1  = TN.ReLU            ()
		self.conv2  = TN.Conv2d          ( 64, 128, (3,3), padding=1, stride=2)
		self.bn2    = TN.BatchNorm2d     (128,  affine=False)
		self.relu2  = TN.ReLU            ()
		self.conv3  = TN.Conv2d          (128, 128, (3,3), padding=1)
		self.bn3    = TN.BatchNorm2d     (128,  affine=False)
		self.relu3  = TN.ReLU            ()
		self.conv4  = TN.Conv2d          (128, 128, (3,3), padding=1)
		self.bn4    = TN.BatchNorm2d     (128,  affine=False)
		self.relu4  = TN.ReLU            ()
		self.conv5  = TN.Conv2d          (128, 256, (3,3), padding=1, stride=2)
		self.bn5    = TN.BatchNorm2d     (256,  affine=False)
		self.relu5  = TN.ReLU            ()
		self.conv6  = TN.Conv2d          (256, 256, (3,3), padding=1)
		self.bn6    = TN.BatchNorm2d     (256,  affine=False)
		self.relu6  = TN.ReLU            ()
		self.conv7  = TN.Conv2d          (256, 256, (3,3), padding=1)
		self.bn7    = TN.BatchNorm2d     (256,  affine=False)
		self.relu7  = TN.ReLU            ()
		self.conv8  = TN.Conv2d          (256, 256, (3,3), padding=1)
		self.bn8    = TN.BatchNorm2d     (256,  affine=False)
		self.relu8  = TN.ReLU            ()
		self.conv9  = TN.Conv2d          (256,  100 if self.d.dataset == "cifar100" else 10,
		                                            (1,1), padding=0)
		self.pool   = TN.AvgPool2d       ((7,7) if self.d.dataset == "mnist" else (8,8))
		self.celoss = TN.CrossEntropyLoss()
	def forward(self, X, Y):
		v, y     = X.view(-1, 1, 28, 28), Y
		v        = self.relu0(self.bn0(self.conv0(v)))
		v        = self.relu1(self.bn1(self.conv1(v)))
		v        = self.relu2(self.bn2(self.conv2(v)))
		v        = self.relu3(self.bn3(self.conv3(v)))
		v        = self.relu4(self.bn4(self.conv4(v)))
		v        = self.relu5(self.bn5(self.conv5(v)))
		v        = self.relu6(self.bn6(self.conv6(v)))
		v        = self.relu7(self.bn7(self.conv7(v)))
		v        = self.relu8(self.bn8(self.conv8(v)))
		v        = self.pool (self.conv9(v))
		v        = v.view(-1, 10)
		
		ceLoss   = self.celoss(v, y)
		yPred    = T.max(v, 1)[1]
		batchErr = yPred.eq(y).long().sum(0)
		
		return {
			"user/ceLoss":   ceLoss,
			"user/batchErr": batchErr,
			"user/yPred":    yPred,
		}





#
# TTQ model
#

class TTQModel(TN.Module):
	def __init__(self, d):
		super(TTQModel, self).__init__()
		self.d      = d
		self.conv0  = Conv2dTTQ        (  1 if self.d.dataset == "mnist" else 3,
		                                      64, (3,3), padding=1)
		self.bntz0  = BatchNorm2dTz    ( 64, lo=0, hi=0)
		self.conv1  = Conv2dTTQ        ( 64,  64, (3,3), padding=1)
		self.bntz1  = BatchNorm2dTz    ( 64, lo=0, hi=0)
		self.conv2  = Conv2dTTQ        ( 64, 128, (3,3), padding=1, stride=2)
		self.bntz2  = BatchNorm2dTz    (128, lo=0, hi=0)
		self.conv3  = Conv2dTTQ        (128, 128, (3,3), padding=1)
		self.bntz3  = BatchNorm2dTz    (128, lo=0, hi=0)
		self.conv4  = Conv2dTTQ        (128, 128, (3,3), padding=1)
		self.bntz4  = BatchNorm2dTz    (128, lo=0, hi=0)
		self.conv5  = Conv2dTTQ        (128, 256, (3,3), padding=1, stride=2)
		self.bntz5  = BatchNorm2dTz    (256, lo=0, hi=0)
		self.conv6  = Conv2dTTQ        (256, 256, (3,3), padding=1)
		self.bntz6  = BatchNorm2dTz    (256, lo=0, hi=0)
		self.conv7  = Conv2dTTQ        (256, 256, (3,3), padding=1)
		self.bntz7  = BatchNorm2dTz    (256, lo=0, hi=0)
		self.conv8  = Conv2dTTQ        (256, 256, (3,3), padding=1)
		self.bntz8  = BatchNorm2dTz    (256, lo=0, hi=0)
		self.conv9  = Conv2dTTQ        (256, 100 if self.d.dataset == "cifar100" else 10,
		                                          (1,1), padding=0)
		self.pool   = TN.AvgPool2d     ((7,7) if self.d.dataset == "mnist" else (8,8))
		self.celoss = TN.CrossEntropyLoss()
	def forward(self, X, Y):
		self.conv0.reconstrain()
		self.conv1.reconstrain()
		self.conv2.reconstrain()
		self.conv3.reconstrain()
		self.conv4.reconstrain()
		self.conv5.reconstrain()
		self.conv6.reconstrain()
		self.conv7.reconstrain()
		self.conv8.reconstrain()
		self.conv9.reconstrain()
		
		shape = (-1, 1, 28, 28) if self.d.dataset == "mnist" else (-1, 3, 32, 32)
		v, y     = X.view(*shape), Y
		v        = self.bntz0(self.conv0(v))
		v        = self.bntz1(self.conv1(v))
		v        = self.bntz2(self.conv2(v))
		v        = self.bntz3(self.conv3(v))
		v        = self.bntz4(self.conv4(v))
		v        = self.bntz5(self.conv5(v))
		v        = self.bntz6(self.conv6(v))
		v        = self.bntz7(self.conv7(v))
		v        = self.bntz8(self.conv8(v))
		v        = self.pool (self.conv9(v))
		v        = v.view(-1, 100 if self.d.dataset == "cifar100" else 10)
		
		ceLoss   = self.celoss(v, y)
		yPred    = T.max(v, 1)[1]
		batchErr = yPred.eq(y).long().sum(0)
		
		return {
			"user/ceLoss":   ceLoss,
			"user/batchErr": batchErr,
			"user/yPred":    yPred,
		}







#
# TTQ Resnet model
#

class TTQResnetModel(TN.Module):
	def __init__(self, d):
		super(TTQResnetModel, self).__init__()
		self.d      = d
		self.conv0  = Conv2dTTQ        (  1 if self.d.dataset == "mnist" else 3,
		                                      64, (3,3), padding=1)
		self.bntz0  = BatchNorm2dTz    ( 64, lo=0, hi=0)
		self.conv1  = Conv2dTTQ        ( 64,  64, (3,3), padding=1)
		self.bntz1  = BatchNorm2dTz    ( 64, lo=0, hi=0)
		self.conv2  = Conv2dTTQ        ( 64, 128, (3,3), padding=1, stride=2)
		self.bntz2  = BatchNorm2dTz    (128, lo=0, hi=0)
		self.conv3  = Conv2dTTQ        (128, 128, (3,3), padding=1)
		self.bntz3  = BatchNorm2dTz    (128, lo=0, hi=0)
		self.conv4  = Conv2dTTQ        (128, 128, (3,3), padding=1)
		self.bntz4  = BatchNorm2dTz    (128, lo=0, hi=0)
		self.conv5  = Conv2dTTQ        (128, 256, (3,3), padding=1, stride=2)
		self.bntz5  = BatchNorm2dTz    (256, lo=0, hi=0)
		self.conv6  = Conv2dTTQ        (256, 256, (3,3), padding=1)
		self.bntz6  = BatchNorm2dTz    (256, lo=0, hi=0)
		self.conv7  = Conv2dTTQ        (256, 256, (3,3), padding=1)
		self.bntz7  = BatchNorm2dTz    (256, lo=0, hi=0)
		self.conv8  = TN.Conv2d        (256, 256, (3,3), padding=1)
		self.bntz8  = BatchNorm2dTz    (256, lo=0, hi=0)
		self.conv9  = TN.Conv2d        (256, 100 if self.d.dataset == "cifar100" else 10,
		                                          (1,1), padding=0)
		self.pool   = TN.AvgPool2d     ((7,7) if self.d.dataset == "mnist" else (8,8))
		self.celoss = TN.CrossEntropyLoss()
	def forward(self, X, Y):
		self.conv0.reconstrain()
		self.conv1.reconstrain()
		self.conv2.reconstrain()
		self.conv3.reconstrain()
		self.conv4.reconstrain()
		self.conv5.reconstrain()
		self.conv6.reconstrain()
		self.conv7.reconstrain()
		#self.conv8.reconstrain()
		#self.conv9.reconstrain()
		
		shape = (-1, 1, 28, 28) if self.d.dataset == "mnist" else (-1, 3, 32, 32)
		v, y     = X.view(*shape), Y
		v        = self.bntz0(self.conv0(v))
		v        = self.bntz1(self.conv1(v))
		v        = self.bntz2(self.conv2(v))
		vR       = self.bntz3(self.conv3(v))
		vR       = self.bntz4(self.conv4(vR))
		v        = Residual3.apply(v, vR) # v + v Residual
		v        = self.bntz5(self.conv5(v))
		vR       = self.bntz6(self.conv6(v))
		vR       = self.bntz7(self.conv7(vR))
		v        = Residual3.apply(v, vR) # v + v Residual
		v        = self.bntz8(self.conv8(v))
		v        = self.pool (self.conv9(v))
		v        = v.view(-1, 100 if self.d.dataset == "cifar100" else 10)
		
		ceLoss   = self.celoss(v, y)
		yPred    = T.max(v, 1)[1]
		batchErr = yPred.eq(y).long().sum(0)
		
		return {
			"user/ceLoss":   ceLoss,
			"user/batchErr": batchErr,
			"user/yPred":    yPred,
		}



#
# TTQ Resnet32 model
#

class TTQResnet32Model(TN.Module):
	def __init__(self, d):
		super(TTQResnet32Model, self).__init__()
		self.d      = d
		self.conv0  = Conv2dTTQ        (  1 if self.d.dataset == "mnist" else 3,
		                                      16, (3,3), padding=1)
		self.bntz0  = BatchNorm2dTz    ( 16, lo=0, hi=0)
		
		self.bb00   = TTQResnetBB      ( 16,  16, 1)
		self.bb01   = TTQResnetBB      ( 16,  16, 1)
		self.bb02   = TTQResnetBB      ( 16,  16, 1)
		self.bb03   = TTQResnetBB      ( 16,  16, 1)
		self.bb04   = TTQResnetBB      ( 16,  16, 1)
		
		self.bb10   = TTQResnetBB      ( 16,  32, 2)
		self.bb11   = TTQResnetBB      ( 32,  32, 1)
		self.bb12   = TTQResnetBB      ( 32,  32, 1)
		self.bb13   = TTQResnetBB      ( 32,  32, 1)
		self.bb14   = TTQResnetBB      ( 32,  32, 1)
		
		self.bb20   = TTQResnetBB      ( 32,  64, 2)
		self.bb21   = TTQResnetBB      ( 64,  64, 1)
		self.bb22   = TTQResnetBB      ( 64,  64, 1)
		self.bb23   = TTQResnetBB      ( 64,  64, 1)
		self.bb24   = TTQResnetBB      ( 64,  64, 1)
		
		self.pool   = TN.AvgPool2d     ((7,7) if self.d.dataset    == "mnist"    else (8,8))
		
		self.conv4  = TN.Conv2d        ( 64, 100 if self.d.dataset == "cifar100" else 10,
		                                (3,3), padding=1)
		
		self.celoss = TN.CrossEntropyLoss()
	def forward(self, X, Y):
		self.conv0.reconstrain()
		
		self.bb00.reconstrain()
		self.bb01.reconstrain()
		self.bb02.reconstrain()
		self.bb03.reconstrain()
		self.bb04.reconstrain()
		
		self.bb10.reconstrain()
		self.bb11.reconstrain()
		self.bb12.reconstrain()
		self.bb13.reconstrain()
		self.bb14.reconstrain()
		
		self.bb20.reconstrain()
		self.bb21.reconstrain()
		self.bb22.reconstrain()
		self.bb23.reconstrain()
		self.bb24.reconstrain()
		
		shape = (-1, 1, 28, 28) if self.d.dataset == "mnist" else (-1, 3, 32, 32)
		v, y     = X.view(*shape), Y
		
		v        = self.bntz0(self.conv0(v))
		
		v        = self.bb00 (v)
		v        = self.bb01 (v)
		v        = self.bb02 (v)
		v        = self.bb03 (v)
		v        = self.bb04 (v)
		
		v        = self.bb10 (v)
		v        = self.bb11 (v)
		v        = self.bb12 (v)
		v        = self.bb13 (v)
		v        = self.bb14 (v)
		
		v        = self.bb20 (v)
		v        = self.bb21 (v)
		v        = self.bb22 (v)
		v        = self.bb23 (v)
		v        = self.bb24 (v)
		
		v        = self.conv4(self.pool(v))
		v        = v.view(-1, 100 if self.d.dataset == "cifar100" else 10)
		
		ceLoss   = self.celoss(v, y)
		yPred    = T.max(v, 1)[1]
		batchErr = yPred.eq(y).long().sum(0)
		
		return {
			"user/ceLoss":   ceLoss,
			"user/batchErr": batchErr,
			"user/yPred":    yPred,
		}

class TTQResnetBB(TN.Module):
	def __init__(self, in_channels, out_channels, stride):
		super(TTQResnetBB, self).__init__()
		self.in_channels  = in_channels
		self.out_channels = out_channels
		self.stride       = stride
		
		#
		# Bypass Connection
		#
		
		if self.stride != 1 or self.in_channels != self.out_channels:
			self.bp     = Conv2dTTQ        (self.in_channels,
			                                self.out_channels,
			                                (3,3),
			                                stride=self.stride,
			                                padding=1)
		else:
			self.bp     = lambda x:x
		
		#
		# Residual Connection
		#
		
		self.conv0  = Conv2dTTQ        (self.in_channels,  self.in_channels,  (3,3), padding=1)
		self.bntz0  = BatchNorm2dTz    (self.in_channels,                     lo=0, hi=0)
		self.conv1  = Conv2dTTQ        (self.in_channels,  self.out_channels, (3,3), stride=self.stride, padding=1)
		self.bntz1  = BatchNorm2dTz    (self.out_channels, self.out_channels, lo=0, hi=0)
	def reconstrain(self):
		self.conv0.reconstrain()
		self.conv1.reconstrain()
	
	def forward(self, v):
		bpV = self.bp(v) # Bypass
		
		v        = self.conv0(v)
		v        = self.bntz0(v)
		v        = self.conv1(v)
		v        = self.bntz1(v)
		
		return Residual3.apply(bpV, v)



#
# Matthieu Courbariaux model reproduction attempt
#

class MatthieuBNN(ModelConstrained):
	"""
	https://arxiv.org/pdf/1602.02830.pdf
	"""
	def __init__(self, a):
		super().__init__()
		self.a = a
		
		actArgs        = (self.a.override,) if self.a.act == "sign" else ()
		override       = self.a.override
		act            = SignBNN if self.a.act == "sign" else PACT
		inChan         =     1 if self.a.dataset == "mnist"    else  3
		outChan        =   100 if self.a.dataset == "cifar100" else 10
		epsilon        = 1e-4   # Some epsilon
		alpha          = 1-0.9  # Exponential moving average factor for BN.
		
		self.conv1     = Conv2dBNN  (inChan, 128, (3,3), padding=1, H=1, W_LR_scale="Glorot", override=override)
		self.bn1       = BatchNorm2d( 128, epsilon, alpha)
		self.tanh1     = act        (*actArgs)
		self.conv2     = Conv2dBNN  ( 128,  128, (3,3), padding=1, H=1, W_LR_scale="Glorot", override=override)
		self.maxpool2  = MaxPool2d  ((2,2), stride=(2,2))
		self.bn2       = BatchNorm2d( 128, epsilon, alpha)
		self.tanh2     = act        (*actArgs)
		
		self.conv3     = Conv2dBNN  ( 128,  256, (3,3), padding=1, H=1, W_LR_scale="Glorot", override=override)
		self.bn3       = BatchNorm2d( 256, epsilon, alpha)
		self.tanh3     = act        (*actArgs)
		self.conv4     = Conv2dBNN  ( 256,  256, (3,3), padding=1, H=1, W_LR_scale="Glorot", override=override)
		self.maxpool4  = MaxPool2d  ((2,2), stride=(2,2))
		self.bn4       = BatchNorm2d( 256, epsilon, alpha)
		self.tanh4     = act        (*actArgs)
		
		self.conv5     = Conv2dBNN  ( 256,  512, (3,3), padding=1, H=1, W_LR_scale="Glorot", override=override)
		self.bn5       = BatchNorm2d( 512, epsilon, alpha)
		self.tanh5     = act        (*actArgs)
		self.conv6     = Conv2dBNN  ( 512,  512, (3,3), padding=1, H=1, W_LR_scale="Glorot", override=override)
		self.maxpool6  = MaxPool2d  ((2,2), stride=(2,2))
		self.bn6       = BatchNorm2d( 512, epsilon, alpha)
		self.tanh6     = act        (*actArgs)
		
		self.linear7   = LinearBNN  (4*4*512, 1024, H=1, W_LR_scale="Glorot", override=override)
		self.tanh7     = act        (*actArgs)
		self.linear8   = LinearBNN  (1024, 1024, H=1, W_LR_scale="Glorot", override=override)
		self.tanh8     = act        (*actArgs)
		self.linear9   = LinearBNN  (1024,  outChan, H=1, W_LR_scale="Glorot", override=override)
	
	
	def forward(self, X):
		shape = (-1, 1, 28, 28) if self.a.dataset == "mnist" else (-1, 3, 32, 32)
		v = X.view(*shape)
		
		v = v*2-1
		
		v = self.conv1   (v)
		v = self.bn1     (v)
		v = self.tanh1   (v)
		v = self.conv2   (v)
		v = self.maxpool2(v)
		v = self.bn2     (v)
		v = self.tanh2   (v)
		
		v = self.conv3   (v)
		v = self.bn3     (v)
		v = self.tanh3   (v)
		v = self.conv4   (v)
		v = self.maxpool4(v)
		v = self.bn4     (v)
		v = self.tanh4   (v)
		
		v = self.conv5   (v)
		v = self.bn5     (v)
		v = self.tanh5   (v)
		v = self.conv6   (v)
		v = self.maxpool6(v)
		v = self.bn6     (v)
		v = self.tanh6   (v)
		
		v = v.view(v.size(0), -1)
		
		v = self.linear7 (v)
		v = self.tanh7   (v)
		v = self.linear8 (v)
		v = self.tanh8   (v)
		v = self.linear9 (v)
		
		return v
	
	def loss(self, Ypred, Y):
		onehotY   = torch.zeros_like(Ypred).scatter_(1, Y.unsqueeze(1), 1)*2 - 1
		hingeLoss = torch.mean(torch.clamp(1.0 - Ypred*onehotY, min=0)**2)
		return hingeLoss


#
# Simple Feed-Forward
#

class FFBNN(ModelConstrained):
	"""
	https://arxiv.org/pdf/1602.02830.pdf
	"""
	def __init__(self, a):
		super().__init__()
		self.a = a
		
		if self.a.act == "pact":
			actArgs = ()
			act     = PACT
		elif self.a.act == "bipact":
			actArgs = ()
			act     = BiPACT
		else:
			actArgs = (self.a.override,)
			act     = SignBNN
		override       = self.a.override
		inChan         = 3
		outChan        = 100 if self.a.dataset == "cifar100" else 10
		bnArgs         = (1e-5, 1-0.9, False)
		
		self.conv1     = Conv2d     (inChan, 128, (3,3), padding=1)
		self.bn1       = BatchNorm2d( 128, *bnArgs)
		self.act1      = act        (*actArgs)
		self.conv2     = Conv2d     ( 128,  128, (3,3), padding=1)
		self.maxpool2  = MaxPool2d  ((2,2), stride=(2,2))
		self.bn2       = BatchNorm2d( 128, *bnArgs)
		self.act2      = act        (*actArgs)
		
		self.conv3     = Conv2d     ( 128,  256, (3,3), padding=1)
		self.bn3       = BatchNorm2d( 256, *bnArgs)
		self.act3      = act        (*actArgs)
		self.conv4     = Conv2d     ( 256,  256, (3,3), padding=1)
		self.maxpool4  = MaxPool2d  ((2,2), stride=(2,2))
		self.bn4       = BatchNorm2d( 256, *bnArgs)
		self.act4      = act        (*actArgs)
		
		self.conv5     = Conv2d     ( 256,  512, (3,3), padding=1)
		self.bn5       = BatchNorm2d( 512, *bnArgs)
		self.act5      = act        (*actArgs)
		self.conv6     = Conv2d     ( 512,  512, (3,3), padding=1)
		self.maxpool6  = MaxPool2d  ((2,2), stride=(2,2))
		self.bn6       = BatchNorm2d( 512, *bnArgs)
		self.act6      = act        (*actArgs)
		
		self.linear7   = Linear     (4*4*512, 1024)
		self.act7      = act        (*actArgs)
		self.linear8   = Linear     (1024, 1024)
		self.act8      = act        (*actArgs)
		self.linear9   = Linear     (1024,  outChan)
	
	
	def forward(self, X):
		shape = (-1, 3, 32, 32)
		v = X.view(*shape)
		
		v = v*2-1
		
		v = self.conv1   (v)
		v = self.bn1     (v)
		v = self.act1    (v)
		v = self.conv2   (v)
		v = self.maxpool2(v)
		v = self.bn2     (v)
		v = self.act2    (v)
		
		v = self.conv3   (v)
		v = self.bn3     (v)
		v = self.act3    (v)
		v = self.conv4   (v)
		v = self.maxpool4(v)
		v = self.bn4     (v)
		v = self.act4    (v)
		
		v = self.conv5   (v)
		v = self.bn5     (v)
		v = self.act5    (v)
		v = self.conv6   (v)
		v = self.maxpool6(v)
		v = self.bn6     (v)
		v = self.act6    (v)
		
		v = v.view(v.size(0), -1)
		
		v = self.linear7 (v)
		v = self.act7    (v)
		v = self.linear8 (v)
		v = self.act8    (v)
		v = self.linear9 (v)
		
		return v
	
	def loss(self, Ypred, Y):
		CEL = torch.nn.functional.cross_entropy(Ypred, Y)
		L2P = torch.tensor(0, dtype=torch.float32)
		if self.a.act == "pact" or self.a.act == "bipact":
			L2P = self.a.l2*(self.act1.alpha**2 +
			                 self.act2.alpha**2 +
			                 self.act3.alpha**2 +
			                 self.act4.alpha**2 +
			                 self.act5.alpha**2 +
			                 self.act6.alpha**2 +
			                 self.act7.alpha**2 +
			                 self.act8.alpha**2)
		L = CEL+L2P
		return L, {"loss/ce":  CEL,
		           "param/l2": torch.sqrt(L2P)}