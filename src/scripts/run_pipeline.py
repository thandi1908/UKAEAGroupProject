# Load the required data

from scripts.pipeline_tools import (
    classifier_accuracy,
    prepare_data,
    regressor_uncertainty,
    select_unstable_data,
    retrain_regressor,
    uncertainty_change,
)
from scripts.Models import ITGDatasetDF, load_model, ITGDataset
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader
from scripts.utils import train_keys

# TODO: Put some of these variables in a yaml config file

pretrained = {
    "ITG_class": {
        "trained": True,
        # "save_path": "/home/tmadula/UKAEAGroupProject/src/notebooks/classifier_model.pt",
        # "save_path": "/unix/atlastracking/jbarr/UKAEAGroupProject/src/notebooks/classifier_model.pt",
        "save_path": "/Users/thandikiremadula/Desktop/UKAEA_data/classifier_model.pt"
    },
    "ITG_reg": {
        "trained": True,
        # "save_path": "/home/tmadula/UKAEAGroupProject/src/notebooks/regression_model.pt",
        # "save_path": "/unix/atlastracking/jbarr/UKAEAGroupProject/src/notebooks/regression_model.pt",
        "save_path": "/Users/thandikiremadula/Desktop/UKAEA_data/regression_model.pt"
    },
}

# Data loading

# TRAIN_PATH = "/share/rcifdata/jbarr/UKAEAGroupProject/data/train_data_clipped.pkl"
# TRAIN_PATH = "/unix/atlastracking/jbarr/train_data_clipped.pkl"
TRAIN_PATH = "/Users/thandikiremadula/Desktop/UKAEA_data/train_data_clipped.pkl"

# VALIDATION_PATH = "/share/rcifdata/jbarr/UKAEAGroupProject/data/valid_data_clipped.pkl"
# VALIDATION_PATH = "/unix/atlastracking/jbarr/valid_data_clipped.pkl"

VALIDATION_PATH = "/Users/thandikiremadula/Desktop/UKAEA_data/valid_data_clipped.pkl"


train_data, val_data = prepare_data(
    TRAIN_PATH, VALIDATION_PATH, target_column="efiitg_gb", target_var="itg"
)

scaler = StandardScaler()
scaler.fit_transform(train_data.drop(["itg"], axis=1))

train_dataset = ITGDatasetDF(train_data, target_column="efiitg_gb", target_var="itg")
valid_dataset = ITGDatasetDF(train_data, target_column="efiitg_gb", target_var="itg")

# # TODO: further testing of the scale function
train_dataset.scale(scaler)
valid_dataset.scale(scaler)

# Use subsample of validation data for now
#valid_dataset = valid_dataset.sample(100_000)

# Load pretrained models
models = {}
for model in pretrained:
    if pretrained[model]["trained"] == True:
        trained_model = load_model(model, pretrained[model]["save_path"])
        models[model] = trained_model

for model_name in models:
    print(f"Model: {model_name}")
    print(models[model_name])

# Train untrained models (may not be needed)

# Sample subset of data to use in active learning (10K for now)
 # TODO: Needs to be the true training samples used!!!
train_sample = train_dataset.sample(10_000) 
valid_sample = valid_dataset.sample(10_000)


# remove the sampled data points from the dataset
valid_dataset.remove(valid_sample.data.index)

# Pass points through the ITG Classifier and return points that pass (what threshold?)
select_unstable_data(valid_sample, 100, models["ITG_class"])
# classifier_accuracy(valid_sample, target_var='itg')

# Run MC dropout on points that pass the ITG classifier and return
uncertain_loader, ucert_before = regressor_uncertainty(
    valid_sample, models["ITG_reg"], n_runs=10
)
#TODO: Why for the previous function we pass in a dataset but for the next function we pass in a dataloader?
train_loader = DataLoader(train_sample, batch_size=1000, shuffle=True)

# Switching validation dataset to numpy arrays to see if it is quicker
x_array = valid_dataset.data[train_keys].values
y_array = valid_dataset.data["itg"].values
z_array = valid_dataset.data["efiitg_gb"].values
dataset_numpy = ITGDataset(x_array, y_array, z_array)
valid_loader = DataLoader(dataset_numpy, batch_size=10_000, shuffle=True)

prediction_before = models["ITG_reg"].predict(uncertain_loader)

# Retrain Regressor (Further research required)
retrain_regressor(
    train_loader,
    uncertain_loader,
    valid_loader,
    models["ITG_reg"],
    1e-4,
    validation_step=True,
)

prediction_after = models["ITG_reg"].predict(uncertain_loader)

_, ucert_after = regressor_uncertainty(valid_sample, models["ITG_reg"], n_runs=10)
# Pipeline diagnosis (Has the uncertainty decreased for new points)
uncertainty_change(ucert_before, ucert_after)

# Pipeline diagnosis (How has the uncertainty changed for original training points)
