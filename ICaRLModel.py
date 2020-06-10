import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable
import numpy as np
from PIL import Image
from DatasetCIFAR import params
from DatasetCIFAR import ResNet
from DatasetCIFAR import data_set
from DatasetCIFAR.data_set import Dataset 

class ICaRLStruct (nn.Module):
  def __init__(self, n_classes = 100, dataset = None):
    super(ICaRLStruct, self).__init__()
    self.features_extractor = ResNet.resnet32(num_classes = 10)
    self.classifier = nn.Linear(self.features_extractor.fc.out_features, n_classes)

    self.k = 2000
    self.exemplar = [None]*n_classes #lista di vettori; ha 100 elementi, ognuno di dimensione m che contiene gli m examplars
    self.m = 0
    self.dataset = dataset
    self.exemplar_means = None
    #Costruisco exemplar come un vettore di liste: 
    #ogni elemento corrisponde alla lista di exemplar presente per quella specifica classe (l'indice di exemplar indica la classe)
    #ogni lista avrà dimentsione M (variante di task in task dunque)
    #Così per ottenere la lista di exemplar in analisi ogni volta posso usare col come con LWF
    self.means = {}

  def forward(self, x):
    x = self.features_extractor(x)
    x = self.classifier(x)
    return x

  def generateExemplars(self, images, m, idxY):
    '''
    images --> indexes of image from a class (Y) belonging to dataSet
    m --> num of elements to be selected for the class Y 
    '''
    transform = transforms.Compose([transforms.ToTensor(),transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),])
    features = []

    for idx in images:
      self.cuda()
      img = self.dataset._data[idx]
      img = Variable(transform(Image.fromarray(img))).cuda()
      feature = self.features_extractor(img.unsqueeze(0)).data.cpu().numpy()
      '''
      unsqueeze need to allow the network to read a single image. It create a "false" new dimension that simulates the following:
      (n samples, channels, height, width).
      Dunque anche il valore di feature sarà una matrice, ideata per contenere i valori di tutto il batch. 
      Per questo motivo, nella seguente istruzione prendo solo il primo elemento ([0])
      '''
      features.append(feature[0]) 
    features = np.array(features)
    mu = np.mean(features, axis=0)
    phiExemplaresY = []
    exemplaresY = []
    for k in range(0,m): #k parte da 0: ricorda di sommare 1 per media
      phiX = features #le features di tutte le immagini della classe Y
      phiP = np.sum(phiExemplaresY, axis = 0) #ad ogni step K, ho già collezionato K-1 examplars
      
      pK = np.argmin( np.sqrt( mu))
      mu1 = 1/(k+1)* ( phiX + phiP)
      idxEx = np.argmin(np.sqrt(np.sum((mu - mu1) ** 2, axis=1))) #execute the euclidean norm among all the rows in phiX

      exemplaresY.append(images[idxEx])
      phiExemplaresY.append(features[idxEx])
    
    '''
    Put into the exemplar array, at position related to the Y class, the elements obtained during this task
    '''
    self.exemplar[idxY] = np.array(exemplaresY)
