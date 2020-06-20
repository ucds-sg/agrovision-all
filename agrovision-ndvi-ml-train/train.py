import numpy as np
import os
import logging

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, ConcatDataset
from torchvision import transforms

from amlrun import get_AMLRun
from msrest.authentication import ApiKeyCredentials
from azure.storage.blob import BlobServiceClient

class BlobStorage:
    CONNECT_STR = "DefaultEndpointsProtocol=https;AccountName=ndvi;AccountKey=bs7YO3wW930aR4iQYF2a0MuWErGAHXagMp6/Jvrh/lc6CeE0zll1WC9zoJ1ljQfHQGInwuuZAU6FBUfLdzmwdw==;EndpointSuffix=core.windows.net"
    TRAIN_CONTAINER = "train"
    TEST_CONTAINER = "test"
    DEV_CONTAINER = "dev"


class NDVIConvNet(nn.Module):
    def __init__(self):
        super(NDVIConvNet, self).__init__()
        self.conv_1 = nn.Conv2d(1, 1, 4)
        self.maxpool_1 = nn.MaxPool2d(kernel_size=8)
        self.linear = nn.Linear(961, 1)

    def forward(self, inputs):
        batch_size = inputs.shape[0]
        x = self.conv_1(inputs)
        x = self.maxpool_1(x)
        x = x.view(batch_size, -1)

        return self.linear(x)


class NDVIDataSet(Dataset):
    def __init__(self, name):
        self.compose = transforms.Compose([transforms.ToPILImage(), transforms.Resize((256, 256)),\
             transforms.ToTensor()])

        directory_path = os.path.join("./data", name)
        self.numpy_files = []
        self.labels = []
        for file_path in os.listdir(directory_path):
            self.numpy_files.append(np.copy(np.load(os.path.join(directory_path, file_path))))
            self.labels.append(1 if file_path.split("-")[0] == "unhealthy" else 0)

    def __getitem__(self, idx):
        numpy_matrix = np.expand_dims(np.float32(self.numpy_files[idx]), 2)
        numpy_resized = self.compose(numpy_matrix)
        return numpy_resized, torch.Tensor([self.labels[idx]])

    def __len__(self):
        return len(self.labels)

def train():
    n_epochs = 10
    batch_size = 32
    lr = 0.001
    device = "cpu"

    ndvi_train_dataset, ndvi_dev_dataset = NDVIDataSet("train"), NDVIDataSet("dev")
    ndvi_test_dataset = NDVIDataSet("test")
    ndvi_dataset = ConcatDataset([ndvi_train_dataset, ndvi_dev_dataset])
    logging.info("Initialized datasets")

    ndvi_dataloader = DataLoader(ndvi_dataset, batch_size=batch_size)
    ndvi_testloader = DataLoader(ndvi_test_dataset, batch_size=batch_size)
    logging.info("Initialized dataloaders")

    ndvi_convnet = NDVIConvNet()
    ndvi_convnet.to(device)
    logging.info("Initialized Model")

    loss = nn.BCEWithLogitsLoss(reduction="mean")
    optimizer = torch.optim.Adam(ndvi_convnet.parameters(), lr=lr)

    run = get_AMLRun()
    logging.info("Starting run")
    for n_iter in range(n_epochs):
        epoch_loss, epoch_acc = 0, 0
        for iter, (matrix, label) in enumerate(ndvi_dataloader):
            matrix, label = matrix.to(device), label.to(device)
            logprobs = ndvi_convnet(matrix)

            batch_loss = loss(logprobs, label)

            ndvi_convnet.zero_grad()
            batch_loss.backward()
            optimizer.step()

            epoch_loss += batch_loss.cpu().item()
            y_pred = torch.sigmoid(logprobs)

            pred_y = y_pred >= 0.5  # a Tensor of 0s and 1s
            num_correct = torch.sum(label == pred_y)
            epoch_acc += num_correct.item()

        logging.info("Epoch Loss: ", epoch_loss)
        logging.info("Epoch Acc: ", epoch_acc/len(ndvi_dataset))

        if n_iter%5 == 0:
            test_acc = 0
            logging.info("Test Acc")
            for iter, (matrix, label) in enumerate(ndvi_testloader):
                with torch.no_grad():
                    matrix, label = matrix.to(device), label.to(device)
                    logprobs = ndvi_convnet(matrix)

                    y_pred = torch.sigmoid(logprobs)
                    pred_y = y_pred >= 0.5       # a Tensor of 0s and 1s
                    num_correct = torch.sum(label == pred_y)  # a Tensor
                    test_acc += num_correct.item()

            if run is not None:
                run.log("Test Acc : ", test_acc/len(ndvi_test_dataset))

        if run is not None:
            run.log('Train Loss', epoch_loss)
            run.log('Training Accuracy', np.float(epoch_acc))

    logging.info("Saving Model")
    torch.save(ndvi_convnet.state_dict(), open("./models/ndvi-mlmodel.pt", "wb"))


train()
