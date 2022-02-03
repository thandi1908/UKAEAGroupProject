import comet_ml
import torch
from pytorch_lightning import Trainer
from torch.utils.data import DataLoader
from pytorch_lightning.plugins import DDPPlugin

from AutoEncoder import Encoder, Decoder, AutoEncoder, AutoEncoderDataset
from scripts.utils import train_keys, target_keys, prepare_model, callbacks 

hyper_parameters = {
    'batch_size': 2048,
    'epochs': 100,
    'learning_rate': 0.002,
}

num_gpu = 3 # Make sure to request this in the batch script
accelerator = 'gpu'

run = "3"

train_data_path = "/share/rcifdata/jbarr/UKAEAGroupProject/data/QLKNN_train_data.pkl"
val_data_path = "/share/rcifdata/jbarr/UKAEAGroupProject/data/QLKNN_validation_data.pkl"
test_data_path = "/share/rcifdata/jbarr/UKAEAGroupProject/data/QLKNN_test_data.pkl"

comet_project_name = 'AutoEncoder'

def main():
    # Load data and create logger for training
    experiment_name = f"Run-{run}"
    keys = train_keys
    comet_logger, train_data, val_data, test_data = prepare_model(train_data_path, val_data_path,
    test_data_path, AutoEncoderDataset, keys, comet_project_name, experiment_name)

    # Create model
    model = AutoEncoder(n_input = 15, latent_dims = 2 **hyper_parameters)
    print(model)

    # Log hyperparameters
    comet_logger.log_hyperparams(hyper_parameters)

    # Create data loaders
    train_loader = DataLoader(train_data, batch_size = hyper_parameters['batch_size'], shuffle = True, num_workers = 20)
    val_loader = DataLoader(val_data, batch_size = hyper_parameters['batch_size'], shuffle = False, num_workers = 20)
    test_loader = DataLoader(test_data, batch_size = hyper_parameters['batch_size'], shuffle = False, num_workers = 20)

    # Create callbacks
    callback_list = callbacks(
        directory = comet_project_name, run = run, experiment_name = experiment_name, top_k = 3)

    # Create trainer
    trainer = Trainer(max_epochs = hyper_parameters['epochs'],
        logger = comet_logger,
        accelerator = accelerator,
        strategy = DDPPlugin(find_unused_parameters = False),
        devices = num_gpu,
        callbacks = callback_list,
        log_every_n_steps = 50)

    # Train model
    trainer.fit(model, train_loader, val_loader)

    # Evaluate model
    trainer.test(dataloaders = test_loader)


if __name__ == '__main__':
    main()