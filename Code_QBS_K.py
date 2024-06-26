# -*- coding: utf-8 -*-
"""Optuna+Sch_QBS.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1YZ193KGFUWl1wntIdzQSFv6CYF5lsOj3

"""

# Commented out IPython magic to ensure Python compatibility.
import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
import math

#Optuna
import optuna
from optuna.trial import TrialState

#Use GPUs to speed up code
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(device)

def plot_losses(loss,a,mu,lossF=None,lossG=None):
	"""
	Function that plots the evolution of the loss function(s) over the epoch.
	Receives as arguments:
	- loss - The "Global" Loss function (list of values for each epoch);
	- a - the spin parameter (int);
	- lossF - the loss of the radial solution (list of values for each epoch);
	- lossG - the loss of the angular solution (list of values for each epoch);
	"""
	plt.figure()
	plt.title(f"Loss over epoch for a={a} and $\mu$={mu}")
	# convert y-axis to Logarithmic scale
	plt.yscale("log")
	plt.plot(loss,label="total loss")
	if None not in (lossF, lossG):
		plt.plot(lossF,label="Loss of F")
		plt.plot(lossG,label="Loss of G")

	plt.legend()
	plt.xlabel("Epoch")
	plt.ylabel("Loss")
	plt.show()
	plt.savefig(f"Loss_over_epoch_a={a}_mu={mu}.png")

def Detweiler(l,m,a,mu,n=0,M=1):
	"""
	Defines the initial values of the frequencies, using Detweiler (1980) approximation.
	Receives as arguments:
	- l,m - Spherical harmonic indicies l and m;
	- a - the spin parameter, value between 0 and 1 (float);
	- mu - the mass of the particle that is perturbing the black hole (float);
	- n - Spherical harmonic indice n, as default we use the fundamental mode
	- M - Mass of the black hole (default = 1)
	Returns:
	- w_real - the frequency of the perturbation (float);
	- w_img - the damping time of the perturbation (float);
	"""

	rplus = M + np.sqrt(M**2 - a**2)

	prod = 1

	for j in range(1,l+1):
		prod = prod * (j**2 * (1 - a**2 / M**2) + (a*m / M - 2*mu*rplus)**2)

	w_real = mu

	w_img = mu * (mu * M)**(4*l+4) * (a*m / M - 2*mu*rplus) * \
	(2**(4*l+2) * math.factorial(2*l + 1 + n)) / ((l+1+n)**(2*l+4) * math.factorial(n)) * \
	(math.factorial(l) / (math.factorial(2*l) * math.factorial(2*l+1) ) )**2 *\
	prod

	return w_real, w_img

def F_terms(a,w,A,m,x,mu,sign,M=1):
	"""
	All these values were calculated by Mathematica.
	Calculates The F_i terms defined in the Appendix A, each one with shape (N_x,1).
	Receives as arguments:
	- a - the spin parameter, value between 0 and 1 (float);
	- w - the frequency of the QNM (parameter of the Neural Network);
	- A - the separation constant of thr Teukolsky equation (parameter of the Neural Network);
	- m - the azimuthal number of the perturbation;
	- x: vector with dimensions (N_x,1) that defines the radial space (compactified radial coordiante).
	- mu: the mass of the particle that is perturbing the black hole (float);
	- sign : the sign of the frequency (1 for QNM and -1 for QNMs);
	- M: the mass of the black hole (float, default value = 1).
	"""

	# Important intermediate values:
	rminus = M - np.sqrt(M**2 - a**2)
	rplus = M + np.sqrt(M**2 - a**2)
	q = sign * torch.sqrt(-w**2 + mu**2)
	w1 = -1j* q
	xi = (mu**2 - 2*w**2)/q
	wc = a*m / (2*M*rplus)# Critical frequency for the superradiance
	sigma = 2 * rplus * (w - wc) / (rplus - rminus)

	if (a == 0):
		#These terms are doing according Kerr_QBS_SamNotation.nb, the last particular case with a = 0
		# F0 term:
		F0 = ((-mu**2 + q**2 + w**2)*xi**2 - 2*x*xi*(-(mu**2*(M + rminus + rplus)*xi) + q**2*(2*M + rminus + rplus)*xi + (rminus + rplus)*w**2*xi - q*(1 + xi)) + 2*M*rminus*rplus*x**7*xi*(A*rminus*rplus*xi +\
		2j*M*rminus*sigma*xi + 2*M*rplus*(-1 + q*rminus*xi - 1j*sigma*xi)) + x**2*(1 + xi*(1 - 2*q*(4*M + rminus + 2*rplus) - A*xi + (4*M**2*q**2 - 4*q*(rminus + rplus) + q**2*(rminus**2 + 4*rminus*rplus +\
		rplus**2) + M*(-6*q - 4*mu**2*(rminus + rplus) + 8*q**2*(rminus + rplus)) + 2j*q*(rminus - rplus)*sigma - (rminus**2 + 4*rminus*rplus + rplus**2)*(mu - w)*(mu + w))*xi)) - 2*x**3*(rplus + \
		2*M**2*q*xi*(-2 + (-1 + 2*q*(rminus + rplus))*xi) + xi*(rminus + rplus - 2*q*rminus*rplus - q*rplus**2 - 1j*rminus*sigma + 1j*rplus*sigma - (A*(rminus + rplus) - q**2*rminus*rplus*(rminus +\
		rplus) + q*(rminus**2 + 4*rminus*rplus + rplus**2 - 1j*(rminus - rplus)*(rminus + rplus)*sigma) + rminus*rplus*(rminus + rplus)*(mu - w)*(mu + w))*xi) + M*(2 + xi - 4*q*(rminus + 2*rplus)*xi -\
		(A + 6*q*(rminus + rplus) + mu**2*(rminus**2 + 4*rminus*rplus + rplus**2) - 2*q**2*(rminus**2 + 4*rminus*rplus + rplus**2) - 4j*q*(rminus - rplus)*sigma)*xi**2)) + x**6*(-(A*rminus**2*rplus**2*xi**2)\
		- 2*M*rminus*rplus*xi*(-3*rplus + (3*q*rminus*rplus + 2*A*(rminus + rplus) + 3j*(rminus - rplus)*sigma)*xi) + 4*M**2*(rplus**2 + 2*rplus*(rminus - q*rminus*rplus - 1j*rminus*sigma +\
		1j*rplus*sigma)*xi + (q*rminus*rplus*(-2*rplus + rminus*(-2 + q*rplus)) + 2j*q*rminus*(rminus - rplus)*rplus*sigma - (rminus - rplus)**2*sigma**2)*xi**2)) + x**4*(-(rminus**2*(A + sigma*(1j +\
		sigma))*xi**2) + 2*M*(4*rplus + 3*rminus*xi + 2*(rplus - 2*q*rplus*(2*rminus + rplus) + 2j*(-rminus + rplus)*sigma)*xi - (2*A*(rminus + rplus) + 2*mu**2*rminus*rplus*(rminus + rplus) -\
		4*q**2*rminus*rplus*(rminus + rplus) + 3*q*(rminus**2 + 4*rminus*rplus + rplus**2) + 1j*(-rminus + rplus)*sigma - 4j*q*(rminus - rplus)*(rminus + rplus)*sigma)*xi**2) + 2*rminus*rplus*xi*(2 -\
		2*(A + q*rminus)*xi + sigma**2*xi + 1j*sigma*(-1 + q*rminus*xi)) + rplus**2*(1 + xi*(1 - 2*q*rminus + 2j*sigma - (A - q**2*rminus**2 + 2*q*rminus*(2 + 1j*sigma) + sigma*(-1j + sigma) +\
		rminus**2*(mu - w)*(mu + w))*xi)) + 4*M**2*(1 + q*xi*(q*rminus**2*xi + rplus*(-4 + (-2 + q*rplus - 2j*sigma)*xi) + rminus*(-2 + (-2 + 4*q*rplus + 2j*sigma)*xi)))) + 2*x**5*(rminus*rplus*xi*(-rplus +\
		(q*rminus*rplus + A*(rminus + rplus) + 1j*(rminus - rplus)*sigma)*xi) + M*(-2*rplus**2 + rplus*(-6*rminus - rplus + 4*q*rminus*rplus + 4j*(rminus - rplus)*sigma)*xi + (A*(rminus**2 + 4*rminus*rplus +\
		rplus**2) + rminus*rplus*(mu**2*rminus*rplus - 2*q**2*rminus*rplus + 6*q*(rminus + rplus)) - 1j*(rminus - rplus)*(-rplus + rminus*(-1 + 4*q*rplus))*sigma + 2*(rminus - rplus)**2*sigma**2)*xi**2) +\
		2*M**2*(q*rplus**2*xi*(2 + xi - 2*q*rminus*xi + 2j*sigma*xi) + rminus*xi*(-1 + q*rminus*xi - 1j*sigma*(-2 + xi + 2*q*rminus*xi)) + rplus*(-2 + xi*(1j*sigma*(-2 + xi) - 2*q**2*rminus**2*xi +\
		4*q*rminus*(1 + xi))))))/((-1 + rminus*x)**2*xi**2)

		# F1 term:
		F1 = (2*x**2*(-1 + 2*M*x)*(-1 + rplus*x)*(x*(-1 + 2*M*x)*(-1 + rplus*x) - q*(-1 + 2*M*x)*(-1 + rminus*x)*(-1 + rplus*x)*xi + x**2*(M + 1j*(rminus - rplus)*sigma + M*x*(rplus*(-1 + 2j*sigma) +\
		rminus*(-1 - 2j*sigma + rplus*x)))*xi))/((-1 + rminus*x)*xi)

		# F2 term:
		F2 = x**4*(1 - 2*M*x)**2*(-1 + rplus*x)**2

	else:
		#These terms are doing according Kerr_QBS_SamNotation.nb, the last particular case with a != 0
		# F0 term:

		F0 = ((-mu**2 + q**2 + w**2)*xi**2 - 2*x*xi*(-(mu**2*(M + rminus + \
		rplus)*xi) + q**2*(2*M + rminus + rplus)*xi + (rminus + \
		rplus)*w**2*xi - q*(1 + xi)) + x**2*(1 + xi*(1 - 8*M*q - 2*q*(rminus \
		+ 2*rplus) + 4*M**2*q**2*xi - 4*q*(rminus + rplus)*xi + q**2*(2*a**2 \
		+ rminus**2 + 4*rminus*rplus + rplus**2)*xi + 2*M*(-2*mu**2*(rminus + \
		rplus) + q*(-3 + 4*q*(rminus + rplus)))*xi + 2j*q*(rminus - \
		rplus)*sigma*xi - (A + (a**2 + rminus**2 + 4*rminus*rplus + \
		rplus**2)*(mu - w)*(mu + w))*xi)) + \
		x**8*(a**2*rminus*rplus*xi*(2*M*rplus + (-A + m**2 - \
		2*M*q)*rminus*rplus*xi - 2j*M*(rminus - rplus)*sigma*xi) + \
		a**4*(rplus**2 - rplus*(rplus + 2*q*rminus*rplus + 2j*rminus*sigma - \
		2j*rplus*sigma)*xi + (q**2*rminus**2*rplus**2 + 1j*(rminus - \
		rplus)*(rminus + rplus + 2*q*rminus*rplus)*sigma - (rminus - \
		rplus)**2*sigma**2)*xi**2)) - \
		2*x**7*(2*a*M*rminus**2*rplus**2*w*xi**2 - \
		M*rminus*rplus*xi*(-2*M*rplus + (A + 2*M*q)*rminus*rplus*xi + \
		2j*M*(rminus - rplus)*sigma*xi) + a**4*(rplus - (rplus + \
		q*rplus*(2*rminus + rplus) + 1j*(rminus - rplus)*sigma)*xi + \
		(q**2*rminus*rplus*(rminus + rplus) + 1j*(rminus - rplus)*(1 + \
		q*(rminus + rplus))*sigma)*xi**2) + a**2*(rminus*rplus*xi*(rplus + \
		rminus*(-A + m**2 - 1j*sigma)*xi + rplus*(-A + m**2 - q*rminus + \
		1j*sigma)*xi) + M*(2*rplus**2 - rplus*(-2*rminus + rplus + \
		4*q*rminus*rplus + 4j*(rminus - rplus)*sigma)*xi + \
		(2*q**2*rminus**2*rplus**2 + 2j*q*rminus*rplus*(1j*(rminus + rplus) + \
		2*(rminus - rplus)*sigma) + (rminus - rplus)*sigma*(1j*(rminus + \
		rplus) + 2*(-rminus + rplus)*sigma) - \
		rminus**2*rplus**2*w**2)*xi**2))) + x**4*(4*M**2 + 8*M*rplus + \
		rplus**2 + a**4*q**2*xi**2 + 8*a*M*(rminus + rplus)*w*xi**2 + a**2*(2 \
		- 4*q*(2*M + rminus + 2*rplus)*xi + (-A + m**2 - 4*q*(rminus + rplus) \
		+ 2*q**2*(rminus**2 + 4*rminus*rplus + rplus**2) + 2*M*q*(-1 + \
		4*q*(rminus + rplus)) + 4j*q*(rminus - rplus)*sigma - 4*M*(rminus + \
		rplus)*w**2 - (rminus**2 + 4*rminus*rplus + rplus**2)*(mu - w)*(mu + \
		w))*xi**2) + xi*(-(rminus**2*(A - q**2*rplus**2 + 2*q*rplus*(2 - \
		1j*sigma) + sigma*(1j + sigma) + rplus**2*(mu - w)*(mu + w))*xi) + \
		2*M*(3*rminus + 2*rplus - 8*q*rminus*rplus - 4*q*rplus**2 - \
		4j*rminus*sigma + 4j*rplus*sigma - (2*A*(rminus + rplus) + \
		2*mu**2*rminus*rplus*(rminus + rplus) - 4*q**2*rminus*rplus*(rminus + \
		rplus) + 3*q*(rminus**2 + 4*rminus*rplus + rplus**2) + 1j*(-rminus + \
		rplus)*sigma - 4j*q*(rminus - rplus)*(rminus + rplus)*sigma)*xi) + \
		rplus**2*(1 + 2j*sigma - (A + sigma*(-1j + sigma))*xi) + \
		4*M**2*q*(q*rminus**2*xi + rplus*(-4 + (-2 + q*rplus - 2j*sigma)*xi) \
		+ rminus*(-2 + (-2 + 4*q*rplus + 2j*sigma)*xi)) - 2*rminus*rplus*(-2 \
		+ 2*A*xi + q*rplus*(1 + (2 + 1j*sigma)*xi) + sigma*(1j - sigma*xi)))) \
		+ x**6*(-(A*rminus**2*rplus**2*xi**2) + 8*a*M*rminus*rplus*(rminus + \
		rplus)*w*xi**2 - 2*M*rminus*rplus*xi*(-3*rplus + 2*A*rminus*xi + \
		(2*A*rplus + 3*q*rminus*rplus + 3j*(rminus - rplus)*sigma)*xi) + \
		a**4*(1 + xi*(-1 - 2*q*(rminus + 2*rplus) + q*(q*(rminus**2 + \
		4*rminus*rplus + rplus**2) + 2j*(rminus - rplus)*sigma)*xi)) + \
		4*M**2*(-(rminus**2*sigma**2*xi**2) + 2*rminus*rplus*xi*(1 - \
		q*rminus*xi + sigma**2*xi + 1j*sigma*(-1 + q*rminus*xi)) + \
		rplus**2*(1 + xi*(-2*q*rminus + 2j*sigma + (q*rminus*(-2 + q*rminus) \
		- 2j*q*rminus*sigma - sigma**2)*xi))) + a**2*(rminus**2*(-A + m**2 - \
		2*sigma**2)*xi**2 + 4*rminus*rplus*xi*(1 - 1j*sigma + (-A + m**2 + \
		sigma**2 + 1j*q*rminus*(1j + sigma))*xi) + 2*M*(4*rplus + rminus*xi - \
		2*(rplus + 2*q*rplus*(2*rminus + rplus) + 2j*(rminus - \
		rplus)*sigma)*xi + (4*q**2*rminus*rplus*(rminus + rplus) - \
		q*(rminus**2 + 4*rminus*rplus + rplus**2) + 3j*(rminus - rplus)*sigma \
		+ 4j*q*(rminus - rplus)*(rminus + rplus)*sigma - \
		2*rminus*rplus*(rminus + rplus)*w**2)*xi**2) + rplus**2*(2 + \
		xi*(-4*q*rminus + 4j*sigma - (A - m**2 - 2*q**2*rminus**2 + \
		2*sigma**2 + 4*q*(rminus + 1j*rminus*sigma) + rminus**2*(mu - w)*(mu \
		+ w))*xi)))) - 2*x**5*(2*a*M*(rminus**2 + 4*rminus*rplus + \
		rplus**2)*w*xi**2 + a**4*q*xi*(-1 + q*(rminus + rplus)*xi) - \
		rminus*rplus*xi*(-rplus + (q*rminus*rplus + A*(rminus + rplus) + \
		1j*(rminus - rplus)*sigma)*xi) + M*(2*rplus**2 + rplus*(6*rminus + \
		rplus - 4*q*rminus*rplus + 4j*(-rminus + rplus)*sigma)*xi - \
		(A*(rminus**2 + 4*rminus*rplus + rplus**2) + \
		rminus*rplus*(mu**2*rminus*rplus - 2*q**2*rminus*rplus + 6*q*(rminus \
		+ rplus)) - 1j*(rminus - rplus)*(-rplus + rminus*(-1 + \
		4*q*rplus))*sigma + 2*(rminus - rplus)**2*sigma**2)*xi**2) + \
		a**2*(rplus**2*xi*(-2*q + (-(mu**2*rminus) + q*(-1 + 2*q*rminus - \
		2j*sigma) + rminus*w**2)*xi) + rminus*xi*(1 - (A - m**2 + \
		q*rminus)*xi + 1j*sigma*(-2 + xi + 2*q*rminus*xi)) + M*(2 + xi*(-1 - \
		4*q*(rminus + 2*rplus) + (-2*q*(rminus + rplus) + 2*q**2*(rminus**2 + \
		4*rminus*rplus + rplus**2) + 4j*q*(rminus - rplus)*sigma - (rminus**2 \
		+ 4*rminus*rplus + rplus**2)*w**2)*xi)) + rplus*(2 + xi*(-4*q*rminus \
		+ 2j*sigma + (-A + m**2 - 1j*sigma + rminus*(-(mu**2*rminus) + \
		2*q*(-2 + q*rminus) + rminus*w**2))*xi))) + 2*M**2*(q*rplus**2*xi*(-2 \
		+ (-1 + 2*q*rminus - 2j*sigma)*xi) + rminus*xi*(1 - q*rminus*xi + \
		1j*sigma*(-2 + xi + 2*q*rminus*xi)) + rplus*(2 + xi*(-1j*sigma*(-2 + \
		xi) + 2*q**2*rminus**2*xi - 4*q*rminus*(1 + xi))))) - 2*x**3*(rplus + \
		2*M**2*q*xi*(-2 + (-1 + 2*q*(rminus + rplus))*xi) + xi*(rminus + \
		rplus - q*rplus*(2*rminus + rplus) - 1j*(rminus - rplus)*sigma + \
		q**2*rminus*rplus*(rminus + rplus)*xi + q*(-4*rminus*rplus + \
		rplus**2*(-1 - 1j*sigma) + 1j*rminus**2*(1j + sigma))*xi - (rminus + \
		rplus)*(A + rminus*rplus*(mu - w)*(mu + w))*xi + a**2*(2*q**2*(rminus \
		+ rplus)*xi - (rminus + rplus)*(mu - w)*(mu + w)*xi - q*(2 + xi))) + \
		M*(2 + xi*(1 + 2*q**2*(a**2 + rminus**2 + 4*rminus*rplus + \
		rplus**2)*xi - (A + mu**2*(rminus**2 + 4*rminus*rplus + rplus**2) + \
		a*w*(-2 + a*w))*xi + q*(2*rplus*(-4 - 3*xi - 2j*sigma*xi) + \
		rminus*(-4 - 6*xi + 4j*sigma*xi))))))/((-1 + rminus*x)**2*xi**2)

		# F1 term:
		F1 = (2*x**2*(-1 + rplus*x)*(1 - 2*M*x + a**2*x**2)*(x*(-1 + rplus*x)*(1 - \
		2*M*x + a**2*x**2) - q*(-1 + rminus*x)*(-1 + rplus*x)*(1 - 2*M*x + \
		a**2*x**2)*xi + x**2*(-M - 1j*(rminus - rplus)*sigma + a**2*x + \
		M*(rminus + rplus + 2j*(rminus - rplus)*sigma)*x - (M*rminus*rplus + \
		a**2*(rminus + rplus + 1j*(rminus - rplus)*sigma))*x**2 + \
		a**2*rminus*rplus*x**3)*xi))/((-1 + rminus*x)*xi)

		# F2 term:
		F2 = x**4*(-1 + rplus*x)**2*(1 - 2*M*x + a**2*x**2)**2
		


	#If value of F0 is Nan, stop the program and print the values of the parameters:
	if torch.isnan(F0).any():
		print("F0 is Nan!")
		#Print the values of all the arguments:
		print(f"a = {a}")
		print(f"w = {w}")
		print(f"A = {A}")
		print(f"m = {m}")
		print(f"x = {x}")
		print(f"mu = {mu}")
		print(f"sign = {sign}")
		print(f"M = {M}")
		exit()


	return F0,F1,F2

def G_terms(a,w,A,m,u,mu,sign):
	"""
	Calculates The F_i terms defined in the Appendix A, each one with shape (N_x,1).
	Receives as arguments:
	- a - the spin parameter, value between 0 and 0.5 (float);
	- w - the frequency of the QNM (parameter of the Neural Network);
	- A - the separation constant of thr Teukolsky equation (parameter of the Neural Network).
	- m - Spherical harmonic indicies l and m;
	- u: vector with dimensions (N_u,1) that defines the angular space.
	- mu: the mass of the particle that is perturbing the black hole (float);
	- sign : the sign of the frequency (1 for QNM and -1 for QNMs).
	"""

	# Important intermediate values:
	w1 = sign*torch.sqrt(w**2 - mu**2)
	b = - 1 + u**2

	G0 =m**2 + b*(A + a*(-2*u*w1 + a*(w1**2))) - b*(1 + 2*a*u*w1)*torch.abs(m) - m**2 * u**2

	G1 = -2*b*(u + a*b*w1 + u*torch.abs(m))

	G2 = -b**2


	return G0,G1,G2


def gradients(outputs, inputs, order = 1):
	"""
	Compute the derivatives of a complex function f(x) via automatic differentiation.

	-param outputs- PyTorch complex tensor of shape (N, 1) with the values of f(x)
	-param inputs-  PyTorch real tensor of shape (N, 1) with the values of x
	-param order-   Order of the derivative (default: 1)
	-return-        PyTorch complex tensor of shape (N, 1) with the values of f'(x)
	"""

	re_outputs = torch.real(outputs)
	im_outputs = torch.imag(outputs)
	if order == 1:
		d_re = torch.autograd.grad(re_outputs, inputs, grad_outputs=torch.ones_like(re_outputs), create_graph=True)[0]
		d_im = torch.autograd.grad(im_outputs, inputs, grad_outputs=torch.ones_like(im_outputs), create_graph=True)[0]
		return d_re + (1j) * d_im
	elif order > 1:
		return gradients(gradients(outputs, inputs, 1), inputs, order - 1)
	else:
		return outputs

class NeuralNetwork(nn.Module):
	"""
	Defines both Neural Networks, for F and G. Returns the hard enforced values of both radial and angular functions.
	Receives as arguments:
	-l,m - Spherical harmonic indicies l and m;
	- input_size_x, input_size_u - The input size of each neural network (1)
	- hidden_layers - number of hidden layers
	- neurons_per_layer - number of neurons per each hidden layer
	- ouput_size - size of the output of the neural network(=2, separation of real and imaginary part)
	- n - Spherical harmonic indice n, as default we use the fundamental mode
	"""

	def __init__(self,activation,std_radial,std_ang_optuna,random_seed, l, m, init_w_real,init_w_img, input_size_x = 1, input_size_u = 1, hidden_layers = 3,neurons_per_layer = 200, output_size = 2 ,n = 0):
		super(NeuralNetwork, self).__init__()

		#Spherical harmonic indicies l and m
		self.l = torch.tensor(l)
		self.m = torch.tensor(m)
		self.n = torch.tensor(n)

		#Activation function
		if activation == "tanh":
			activation = nn.Tanh()
		else:
			print("Activation function not implemented!")
			exit()    

		#Parameters of the Neural Network:

		self.w_real = torch.nn.Parameter(data = torch.tensor(init_w_real), requires_grad = True)
		self.w_img = torch.nn.Parameter(data = torch.tensor(init_w_img), requires_grad = True)

		self.A_real = torch.nn.Parameter(data = torch.tensor(float(l*(l+1)) ), requires_grad = True)
		self.A_img = torch.nn.Parameter(data = torch.tensor(0.0), requires_grad = True)


		#Network for the Radial Equation (depends on x)
		self.x_network = nn.Sequential()
		self.x_network.add_module("Input",nn.Linear(input_size_x, neurons_per_layer))
		self.x_network.add_module("Input activatation",activation)
		for i in range(hidden_layers):
			self.x_network.add_module(f"Hidden layer number: {i+1} ",nn.Linear(neurons_per_layer, neurons_per_layer))
			self.x_network.add_module(f"Hidden {i+1} activation",activation)
		self.x_network.add_module("Output", nn.Linear(neurons_per_layer, output_size))

		#Network for the Angular Equation (depends on u)
		self.u_network = nn.Sequential()
		self.u_network.add_module("Input",nn.Linear(input_size_u, neurons_per_layer))
		self.u_network.add_module("Input activatation",activation)
		for i in range(hidden_layers):
			self.u_network.add_module(f"Hidden layer number: {i+1} ",nn.Linear(neurons_per_layer, neurons_per_layer))
			self.u_network.add_module(f"Hidden {i+1} activation",activation)
		self.u_network.add_module("Output", nn.Linear(neurons_per_layer, output_size))

		#Random initialization of the network parameters:

		#Maybe try different seeds in further tests
		torch.manual_seed(random_seed)

		#Talvez mudar tambem a std da inicialização, secundariamente


		for z in self.x_network.modules():
			if isinstance(z,nn.Linear):
				nn.init.normal_(z.weight,mean = 0,std = std_radial)
				nn.init.constant_(z.bias,val=0)

		for z in self.u_network.modules():
			if isinstance(z,nn.Linear):
				nn.init.normal_(z.weight,mean=0,std= std_ang_optuna)
				nn.init.constant_(z.bias,val=0)
	
	def forward(self, x, u,a):
		"""
		Evaluates the NN and applies the hard enforcement of normalization
		Receives as arguments:
		x,u : the vectors with dimensions (N_x,1) and (N_u,1) that defined
			the radial and angular space, respectively;
			a : the spin parameter, useful for the hard enforcement of the boundary conditions.
		"""

		# calculate r_plus:
		r_plus = 1 + np.sqrt(1-a**2) #Note that this already has M = 1 !!!!!!!!!!!!!

		#Get the value of each NN for x and u  
		x_output = self.x_network(x)
		u_output = self.u_network(u)

		#Clone f and g, turning two collumns into a complex number and turn into a [N_x,1] matrix
		f_complex_tensor = torch.view_as_complex(x_output)
		g_complex_tensor = torch.view_as_complex(u_output)

		#After joining them, one needs to hard enforce f:
		f_new = ((torch.exp(x.view(-1)- (1/r_plus) )-1)*f_complex_tensor + 1).view(-1,1) #Hard Enforcement for f(x)
		g_new = ((torch.exp(u.view(-1)+1)-1)*g_complex_tensor + 1).view(-1,1) #Hard Enforcement for g(u)


		return f_new, g_new

class CustomLoss(nn.Module):
	"""
	Returns the Loss Function, defined here specifically for the Teukolsky Equation
	Receives as arguments:
	- Neural Network - interpolator of the NN;
	- a - the spin parameter, value between 0 and 1 (float);
	- r_plus - outer horizon radii of the Kerr metric (float);
	"""
	def __init__(self,NeuralNetwork,a,mu,sign,w_real,w_img,M=1):
		super(CustomLoss,self).__init__()

		self.NeuralNetwork = NeuralNetwork
		self.a = torch.tensor(a)
		self.mu = torch.tensor(mu)
		self.sign = torch.tensor(sign)
		self.w_real = torch.tensor(w_real)
		self.w_img = torch.tensor(w_img)
		self.M = torch.tensor(M)

		self.l = NeuralNetwork.l
		self.m = NeuralNetwork.m

	def forward(self,x,u,weight_loss_factor_optuna):

		#Compute some commom expressions
		a = self.a
		m = self.m
		l = self.l
		mu = self.mu
		sign = self.sign
		M = self.M

		#Recover eigenvalues

		w_real = self.NeuralNetwork.w_real
		w_img = self.NeuralNetwork.w_img
		A_real = self.NeuralNetwork.A_real
		A_img = self.NeuralNetwork.A_img


		#To call the function F_terms and G_terms, we need to convert the eigenvalues to complex numbers
		w = torch.view_as_complex(torch.stack((w_real,w_img),dim=0))
		A = torch.view_as_complex(torch.stack((A_real,A_img),dim=0))

		# Calculate the F ang G terms for the Loss Function
		F0,F1,F2 = F_terms(a,w,A,m,x,mu,sign,M)
		G0, G1, G2 = G_terms(a,w,A,m,u,mu,sign)

		#Recover the value of the hard enforced f and g
		f, g = self.NeuralNetwork(x,u,a)

		# Compute the derivatives of hard enforced f and g needed for the Loss Function
		dfdt = gradients(outputs = f, inputs = x)
		d2fdt2 = gradients(outputs = dfdt, inputs = x)
		dgdt = gradients(outputs = g, inputs = u)
		d2gdt2 = gradients(outputs = dgdt, inputs = u)

		#Now focus on the radial equation:

		lossF = torch.mean(torch.abs(F2*d2fdt2 + F1*dfdt + F0*f))
		lossG = torch.mean(torch.abs(G2*d2gdt2 + G1*dgdt + G0*g))

		loss =  (10**weight_loss_factor_optuna) * lossF + lossG


		return loss

#Comparison with Leaver's results

def print_results_QNM(w_real, w_img, a):
	"""
	Function that prints the results of the model and compares them with Leaver's results
	Args:
		w_real
        w_img
        a
	Returns:
		None
	"""
	if(a == 0.1):
		Leaver_real = 0.389635
		Leaver_img = -0.00046769
	elif(a == 0.5):
		Leaver_real = 0.390012
		Leaver_img = -0.00015369
	elif(a == 0.9):
		Leaver_real = 0.390438
		Leaver_img = -4.41169*10**-6
	elif(a == 0.95):
		Leaver_real = 0.390487
		Leaver_img = -5.82368*10**-7


	error_real = 100*np.abs(w_real - Leaver_real) / np.abs(Leaver_real)
	#print("Percentual error for the real frequency:\n",error_real)

	error_img = 100*np.abs(w_img - Leaver_img) / np.abs(Leaver_img)
	#print("Percentual error for the imaginary frequency:\n", error_img)

	average_error = (error_real + error_img)/2
	#print("Average error:\n", average_error)

	return error_real, error_img, average_error


def objective (trial):
	# Set double precision as standard for torch
	torch.set_default_dtype(torch.float64)
	#print(device)

	# sample locations over the problem domain
	N_x = 100
	N_u = 100

	#Definition of a and mu
	#a_list  = [0.1, 0.5, 0.9, 0.95]
	a_list = [0.9]
	mu = 0.4
	M = 1 # Mass of the black hole
	sign = -1 # Sign of the frequency (1 for QNM and -1 for QBSs)

	# define the neural network to train
	l,m = 1,1

	"""
	##############################################################################################
	#Values defined by previous studies:
	hidden_layers = 2
	neurons_per_layer = 100
	lr_Adam = 5e-4
	activation = "tanh"
	epochs_Adam = 500
	std_radial = 0.40
	restarts_optuna = 65
	lr_LBFGS = 1e-2
	epochs_LBFGS = 500
	std_ang = 0.18
	weight_loss_factor = 3 # 10**weight_loss_factor 
	##############################################################################################
	"""

	##############################################################################################
	#Optuna values:
	#hidden_layers = trial.suggest_int("hidden_layers", 1, 3)
	hidden_layers = 2
	neurons_per_layer = trial.suggest_int("neurons_per_layer", 250, 300)
	lr_Adam = trial.suggest_float("lr_Adam", 1e-6, 1e-2)
	#activation = trial.suggest_categorical("activation", ["tanh"])
	activation = "tanh"
	epochs_Adam = trial.suggest_int("epochs_Adam", 1500, 3000)
	std_radial = trial.suggest_float("std_radial", 0.01, 0.99)
	restarts_optuna = trial.suggest_int("restarts_optuna", 1, 100)
	lr_LBFGS = trial.suggest_float("lr_LBFGS", 5e-2, 1e-1)
	epochs_LBFGS = trial.suggest_int("epochs_LBFGS", 200, 300)
	std_ang = trial.suggest_float("std_ang", 0.01, 0.99)
	weight_loss_factor = 1
	##############################################################################################

	#Initialize the model
	#Find the best frequency to start the model using the Detweiler's method:
	for a in a_list:

		#Define the spacial domain for each a
		r_plus = M + np.sqrt(M**2 - a**2)
		x = torch.linspace(0,1/r_plus,N_x).view(-1,1).requires_grad_(True).to(device)
		u = torch.linspace(-1,1,N_u).view(-1,1).requires_grad_(True).to(device)
		
		init_w_real, init_w_img = Detweiler(l,m,a,mu)
		model = NeuralNetwork(activation = activation ,std_radial = std_radial,std_ang_optuna = std_ang,random_seed = 15,hidden_layers = hidden_layers , neurons_per_layer = neurons_per_layer  ,l = l, m = m, init_w_real = init_w_real, init_w_img = init_w_img).to(device)

		#Initialize the optimiser
		optimiser = torch.optim.Adam(model.parameters(), lr = lr_Adam)

		scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer = optimiser, T_0 = restarts_optuna )

		#Initialize the model of the loss
		model_loss = CustomLoss(model,a,mu,sign,w_real = init_w_real,w_img = init_w_img).to(device) #Change for different mu
		#Initialize (empty lists) that store values for plots for each a
		loss_list = []
		previous_loss = None

		#Train the model with the ADAM optimiser

		for i in range(epochs_Adam):
			optimiser.zero_grad()
			loss = model_loss(x,u,weight_loss_factor)

			# backpropagate joint loss, take optimiser step
			loss.backward()
			optimiser.step()
			scheduler.step()

			#Update previous loss
			previous_loss = loss.item()

			#record values of loss function
			loss_list.append(loss.item())

			#calculate the accuracy of the model
			accuracy_real, accuracy_img, accuracy_average = print_results_QNM(model.w_real.item(), model.w_img.item(),a)

			trial.report(accuracy_average, i)

			# Handle pruning based on the intermediate value.
			if trial.should_prune():
				raise optuna.exceptions.TrialPruned()



		#Define the closure for the LBFGS optimiser
		optimiser_tuning = torch.optim.LBFGS(model.parameters(), lr = lr_LBFGS)

		def closure():
			optimiser_tuning.zero_grad()
			loss = model_loss(x,u,weight_loss_factor)
			loss.backward()
			return loss

		#Train the model with the fine tuning optimiser
		for j in range(epochs_LBFGS):
			optimiser_tuning.step(closure)

			# Update previous loss
			previous_loss = closure().item()

			# Record values of loss function
			loss_list.append(previous_loss)

			# Calculate the accuracy of the model
			accuracy_real, accuracy_img, accuracy_average = print_results_QNM(model.w_real.item(), model.w_img.item(),a)

			trial.report(accuracy_average, epochs_Adam + j)

			# Handle pruning based on the intermediate value.
			if trial.should_prune():
				raise optuna.exceptions.TrialPruned()
        
        #Plot the loss function
		#plot_losses(loss_list, a, mu)

		#Print the results of the model
		#print("For a = ", a)    
		print("Real frequency:", model.w_real.item())
		print("Imaginary frequency:", model.w_img.item())

		#Print the results of the model and compare with Leaver's results
		accuracy_real, accuracy_img, accuracy_average = print_results_QNM(model.w_real.item(), model.w_img.item(),a)
		print("Average error:", accuracy_average)
		print("Real error:", accuracy_real)
		print("Imaginary error:", accuracy_img)

		return accuracy_average


if __name__ == "__main__":
	study = optuna.create_study(direction = "minimize", pruner = optuna.pruners.HyperbandPruner())
	study.optimize(objective, n_trials = 2000)
	
	pruned_trials = study.get_trials(deepcopy=False, states=[TrialState.PRUNED])
	complete_trials = study.get_trials(deepcopy=False, states=[TrialState.COMPLETE])

	print("Study statistics:")
	print("  Number of finished trials:", len(study.trials))
	print("  Number of pruned trials:", len(pruned_trials))
	print("  Number of complete trials:", len(complete_trials))

	print("Best trial:")
	best_trial = study.best_trial

	print("  Value:", best_trial.value)

	print("  Params:")
	for key, value in best_trial.params.items():
		print("    {}: {}".format(key, value))

"""
[I 2024-04-23 22:20:52,801] Trial 23 finished with value: 41.42598644308909 and parameters: {'neurons_per_layer': 294, 'lr_Adam': 0.0020703458561315605, 'epochs_Adam': 2516, 'std_radial': 0.1312151793633246, 'restarts_optuna': 24, 'lr_LBFGS': 0.08055439918400112, 'epochs_LBFGS': 249, 'std_ang': 0.09901445620375583}. Best is trial 23 with value: 41.42598644308909.
"""