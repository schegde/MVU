# -*- coding: utf-8 -*-



# Imports.
import cPickle                              as pkl
import ipdb
from   ipdb import set_trace as bp
import math
import numpy                                as np
import os
import pysnips.ml.experiment                as PySMlExp
import pysnips.ml.loop                      as PySMlL
import pysnips.ml.pytorch                   as PySMlPy
import sys
import torch                                as T
import torch.autograd                       as TA
import torch.cuda                           as TC
import torch.nn                             as TN
import torch.optim                          as TO
import torch.utils                          as TU
import torch.utils.data                     as TUD
import torchvision                          as Tv
import torchvision.transforms               as TvT
from   models import                        *


class Experiment(PySMlExp.Experiment, PySMlL.Callback):
	def __init__(self, workDir, d):
		super(Experiment, self).__init__(workDir, d=d)
		self.__dataDir = self.d.dataDir
		
		
		"""Dataset Selection"""
		if   self.d.dataset == "mnist":
			self.Dxform  = [TvT.ToTensor()]
			self.Dxform  = TvT.Compose(self.Dxform)
			self.Dtrain  = Tv.datasets.MNIST   (self.dataDir, True,    self.Dxform)
			self.Dtest   = Tv.datasets.MNIST   (self.dataDir, False,   self.Dxform)
			self.Dimgsz  = (1, 28, 28)
			self.DNclass = 10
			self.DNvalid = 10000
		elif self.d.dataset == "cifar10":
			self.Dxform  = [TvT.ToTensor()]
			self.Dxform  = TvT.Compose(self.Dxform)
			self.Dtrain  = Tv.datasets.CIFAR10 (self.dataDir, True,    self.Dxform)
			self.Dtest   = Tv.datasets.CIFAR10 (self.dataDir, False,   self.Dxform)
			self.Dimgsz  = (3, 32, 32)
			self.DNclass = 10
			self.DNvalid = 10000
		elif self.d.dataset == "cifar100":
			self.Dxform  = [TvT.ToTensor()]
			self.Dxform  = TvT.Compose(self.Dxform)
			self.Dtrain  = Tv.datasets.CIFAR100(self.dataDir, True,    self.Dxform)
			self.Dtest   = Tv.datasets.CIFAR100(self.dataDir, False,   self.Dxform)
			self.Dimgsz  = (3, 32, 32)
			self.DNclass = 100
			self.DNvalid = 10000
		elif self.d.dataset == "svhn":
			self.Dxform  = [TvT.ToTensor()]
			self.Dxform  = TvT.Compose(self.Dxform)
			self.Dtrain  = Tv.datasets.SVHN    (self.dataDir, "train", self.Dxform)
			self.Dtest   = Tv.datasets.SVHN    (self.dataDir, "test",  self.Dxform)
			self.Dimgsz  = (3, 32, 32)
			self.DNclass = 10
			self.DNvalid = 10000
		else:
			raise ValueError("Unknown dataset \""+self.d.dataset+"\"!")
		self.DNtotal    = len(self.Dtrain)
		self.DNtest     = len(self.Dtest)
		self.DNtrain    = self.DNtotal-self.DNvalid
		
		
		"""Model Instantiation"""
		self.model = None
		if   self.d.model == "real": self.model = RealModel(self.d)
		elif self.d.model == "ttq":  self.model = TTQModel (self.d)
		if   self.model is None:
			raise ValueError("Unsupported dataset-model pair \""+self.d.dataset+"-"+self.d.model+"\"!")
		
		if self.d.cuda is None:
			self.model.cpu()
		else:
			self.model.cuda(self.d.cuda)
		
		
		
		"""Optimizer Selection"""
		if   self.d.optimizer.name in ["sgd", "nag"]:
			self.optimizer = TO.SGD(self.model.parameters(),
			                        self.d.optimizer.lr,
			                        self.d.optimizer.mom,
			                        nesterov = (self.d.optimizer.name == "nag"))
		elif self.d.optimizer.name == "rmsprop":
			self.optimizer = TO.RMSprop(self.model.parameters(),
			                            self.d.optimizer.lr,
			                            self.d.optimizer.rho,
			                            self.d.optimizer.eps)
		elif self.d.optimizer.name == "adam":
			self.optimizer = TO.Adam(self.model.parameters(),
			                         self.d.optimizer.lr,
			                         (self.d.optimizer.beta1,
			                          self.d.optimizer.beta2),
			                         self.d.optimizer.eps)
		elif self.d.optimizer.name == "yellowfin":
			if False:
				self.optimizer = PySMlPy.YellowFin(self.model.parameters(),
				                                   self.d.optimizer.lr,
				                                   self.d.optimizer.mom,
				                                   self.d.optimizer.beta,
				                                   self.d.optimizer.curvWW,
				                                   self.d.optimizer.nesterov)
			else:
				from pysnips.ml.pytorch.yfoptimizer import YFOptimizer
				self.optimizer = YFOptimizer(self.model.parameters(),
				                             self.d.optimizer.lr,
				                             self.d.optimizer.mom,
				                             clip_thresh    = self.d.clipnorm,
				                             beta           = self.d.optimizer.beta,
				                             curv_win_width = self.d.optimizer.curvWW)
		else:
			raise NotImplementedError("Optimizer "+self.d.optimizer.name+" not implemented!")
	
	
	@property
	def dataDir(self): return self.__dataDir
	@property
	def logDir(self):  return os.path.join(self.workDir, "logs")
	
	
	#
	# Experiment API
	#
	def dump(self, path):
		return self
	def load(self, path):
		return self
	def fromScratch(self):
		super(Experiment, self).fromScratch()
		
		self.loopDict = {
			"std/loop/epochMax": self.d.num_epochs,
			"std/loop/batchMax": len(self.Dtrain)/self.d.batch_size
		}
		
		return self
	def fromSnapshot(self, path):
		super(Experiment, self).fromSnapshot(path)
		return self
	def run(self):
		#
		# With the RNGs properly seeded, create the dataset iterators.
		#
		
		self.DtrainIdx  = range(self.DNtotal)[:self.DNtrain]
		self.DvalidIdx  = range(self.DNtotal)[-self.DNvalid:]
		self.DtestIdx   = range(self.DNtest)
		self.DtrainSmp  = TUD.sampler.SubsetRandomSampler(self.DtrainIdx)
		self.DvalidSmp  = TUD.sampler.SubsetRandomSampler(self.DvalidIdx)
		self.DtestSmp   = TUD.sampler.SubsetRandomSampler(self.DtestIdx)
		self.DtrainLoad = TUD.DataLoader(dataset     = self.Dtrain,
		                                 batch_size  = self.d.batch_size,
		                                 shuffle     = False,
		                                 sampler     = self.DtrainSmp,
		                                 num_workers = 0,
		                                 pin_memory  = False)
		self.DvalidLoad = TUD.DataLoader(dataset     = self.Dtrain,
		                                 batch_size  = self.d.batch_size,
		                                 shuffle     = False,
		                                 sampler     = self.DvalidSmp,
		                                 num_workers = 0,
		                                 pin_memory  = False)
		self.DtestLoad  = TUD.DataLoader(dataset     = self.Dtest,
		                                 batch_size  = self.d.batch_size,
		                                 shuffle     = False,
		                                 sampler     = self.DtestSmp,
		                                 num_workers = 0,
		                                 pin_memory  = False)
		
		#
		# Set up the callback system.
		#
		
		self.callbacks = [
			PySMlL.CallbackProgbar(50),
		] + [self] + [
			PySMlL.CallbackLinefeed(),
			PySMlL.CallbackFlush(),
		]
		
		#
		# Run training loop.
		#
		
		self.loopDict = PySMlL.loop(self.callbacks, self.loopDict)
		
		return self
	
	#
	# Callback API
	#
	
	def anteTrain(self, d): pass
	def anteEpoch(self, d):
		d["user/epochErr"] = 0
		d["user/epochErr"] = 0
		
		self.model.train(True)
		self.DtrainIter = enumerate(self.DtrainLoad)
		self.DvalidIter = enumerate(self.DvalidLoad)
		self.DtestIter  = enumerate(self.DtestLoad)
	def anteBatch(self, d): pass
	def execBatch(self, d):
		b = d["std/loop/batchNum"]
		
		#
		# Load Data
		#
		
		I, (X, Y) = self.DtrainIter.next()
		if self.d.cuda is None:
			X, Y = X.cpu(), Y.cpu()
		else:
			X, Y = X.cuda(self.d.cuda), Y.cuda(self.d.cuda)
		X, Y = TA.Variable(X), TA.Variable(Y)
		
		
		#
		# Feed it to model and step the optimizer
		#
		self.optimizer.zero_grad()
		d.update(self.model(X, Y))
		d["user/ceLoss"].backward()
		self.optimizer.step()
	def postBatch(self, d): pass
	def postEpoch(self, d):
		d.update(self.validate())
		sys.stdout.write(
			"\nValLoss: {:6.2f}  ValAccuracy: {:6.2f}%".format(
				d["user/valLoss"],
				100.0*d["user/valAcc"],
			)
		)
		self.log.write("{:d},{:6.2f},{:6.2f}\n".format(d["std/loop/epochNum"],
		                                               d["user/valLoss"],
		                                               100.0*d["user/valAcc"]))
	def postTrain(self, d): pass
	def finiTrain(self, d): pass
	def finiEpoch(self, d): pass
	def finiBatch(self, d):
		batchNum  = d["std/loop/batchNum"]
		batchSize = self.d.batch_size
		ceLoss    = float(d["user/ceLoss"]  .data.cpu().numpy())
		batchErr  = int  (d["user/batchErr"].data.cpu().numpy())
		d["user/epochErr"] += batchErr
		sys.stdout.write(
			"CE Loss: {:8.6f}  Batch Accuracy: {:6.2f}%  Accuracy: {:6.2f}%".format(
				ceLoss,
				100.0*batchErr/batchSize,
				100.0*d["user/epochErr"]/((batchNum+1)*batchSize)
			)
		)
	def preempt  (self, d):
		if d["std/loop/state"] == "anteEpoch" and d["std/loop/epochNum"] > 0:
			self.snapshot()
	
	def validate (self):
		# Switch to validation mode
		self.model.train(False)
		valErr  = 0
		valLoss = 0
		
		numBatches = len(self.validX) // self.d.batch_size
		
		for b in xrange(numBatches):
			#
			# Get the data...
			#
			X = self.validX[b*self.d.batch_size:(b+1)*self.d.batch_size]
			Y = self.validY[b*self.d.batch_size:(b+1)*self.d.batch_size]
			if self.d.cuda is None:
				X = T. FloatTensor(X)
				Y = T. LongTensor (Y)
			else:
				X = TC.FloatTensor(X)
				Y = TC.LongTensor (Y)
			X = TA.Variable(X)
			Y = TA.Variable(Y)
			
			#
			# Feed it to model and step the optimizer
			#
			d = self.model(X, Y)
			valErr  += int  (d["user/batchErr"].data.cpu().numpy())
			valLoss += float(d["user/ceLoss"]  .data.cpu().numpy())
		
		# Switch back to train mode
		self.model.train(True)
		
		valAcc   = float(valErr) / (numBatches*self.d.batch_size)
		valLoss /= numBatches
		
		return {
			"user/valAcc":  valAcc,
			"user/valLoss": valLoss,
		}

