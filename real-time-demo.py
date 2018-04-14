from __future__ import print_function
import argparse
import os
import random
import torch
import torch.nn as nn
from PIL import Image
import torch.backends.cudnn as cudnn
import torchvision.utils as vutils
from torch.autograd import Variable
import time
from libs.Loader import Dataset
from libs.Matrix import MulLayer
from torch.utils.serialization import load_lua
from libs.models import encoder1,encoder2,encoder3,encoder4
from libs.models import decoder1,decoder2,decoder3,decoder4
import torchvision.transforms as transforms
from libs.utils import makeVideo
import scipy.misc
import numpy as np
import cv2

parser = argparse.ArgumentParser()
parser.add_argument("--vgg_dir", default='models/vgg_normalised_conv3_1.t7', help='maybe print interval')
parser.add_argument("--decoder_dir", default='models/feature_invertor_conv3_1.t7', help='maybe print interval')
parser.add_argument("--style", default="data/style/in2.jpg", help='path to style image')
parser.add_argument("--matrixPath", default="models/r31.pth", help='path to pre-trained model')
parser.add_argument('--loadSize', type=int, default=256, help='image size')
parser.add_argument('--fineSize', type=int, default=256, help='image size')
parser.add_argument("--name",default="test",help="name of generated video")
parser.add_argument("--layer",default="r31",help="which layer")
parser.add_argument("--outf",default="videos",help="which layer")

################# PREPARATIONS #################
opt = parser.parse_args()
opt.cuda = torch.cuda.is_available()
print(opt)

try:
    os.makedirs(opt.outf)
except OSError:
    pass

cudnn.benchmark = True

################# DATA #################
def loadImg(imgPath):
    img = Image.open(imgPath).convert('RGB')
    transform = transforms.Compose([
                transforms.Scale(opt.fineSize),
                transforms.ToTensor()])
    return transform(img)
style = Variable(loadImg(opt.style).unsqueeze(0),volatile=True)
################# MODEL #################
encoder_torch = load_lua(opt.vgg_dir)
decoder_torch = load_lua(opt.decoder_dir)

if(opt.layer == 'r11'):
    matrix = MulLayer(layer='r11')
    vgg = encoder1(encoder_torch)
    dec = decoder1(decoder_torch)
elif(opt.layer == 'r21'):
    matrix = MulLayer(layer='r21')
    vgg = encoder2(encoder_torch)
    dec = decoder2(decoder_torch)
elif(opt.layer == 'r31'):
    matrix = MulLayer(layer='r31')
    vgg = encoder3(encoder_torch)
    dec = decoder3(decoder_torch)
elif(opt.layer == 'r41'):
    matrix = MulLayer(layer='r41')
    vgg = encoder4(encoder_torch)
    dec = decoder4(decoder_torch)
matrix.load_state_dict(torch.load(opt.matrixPath))
for param in vgg.parameters():
    param.requires_grad = False
for param in matrix.parameters():
    param.requires_grad = False

################# GLOBAL VARIABLE #################
content = Variable(torch.Tensor(1,3,opt.fineSize,opt.fineSize),volatile=True)

################# GPU  #################
if(opt.cuda):
    vgg.cuda()
    dec.cuda()
    matrix.cuda()

    style = style.cuda()
    content = content.cuda()

totalTime = 0
imageCounter = 0
result_frames = []
contents = []
styles = []
cap = cv2.VideoCapture(0)
cap.set(3,256)
cap.set(4,512)
fourcc = cv2.VideoWriter_fourcc(*'MJPG')
out = cv2.VideoWriter('out.avi',fourcc,20.0,(512,256))


sF = vgg(style)

while(True):
    ret,frame = cap.read()
    frame = cv2.resize(frame,(512,256),interpolation=cv2.INTER_CUBIC)
    frame = frame.transpose((2,0,1))
    frame = frame[::-1,:,:]
    frame = frame/255.0
    frame = torch.from_numpy(frame.copy()).unsqueeze(0)
    content.data.resize_(frame.size()).copy_(frame)
    cF = vgg(content)
    if(opt.layer == 'r41'):
        feature,transmatrix = matrix(cF[opt.layer],sF[opt.layer])
    else:
        feature,transmatrix = matrix(cF,sF)
    transfer = dec(feature)
    transfer = transfer.clamp(0,1).squeeze(0).data.cpu().numpy()
    transfer = transfer.transpose((1,2,0))
    transfer = transfer[...,::-1]
    #transfer = transfer * 255
    out.write(np.uint8(transfer*255))
    cv2.imshow('frame',transfer)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
out.release()
cap.release()
cv2.destroyAllWindows()