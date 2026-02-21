---
name: python-data-science
description: NumPy, pandas, scikit-learn, matplotlib, data pipelines, feature engineering, model evaluation, reproducibility, Jupyter, spatial, geostatistics
---
# Python Data Science Skill

## Data Loading

### pandas I/O Patterns
```python
import pandas as pd

# CSV with type optimization
df = pd.read_csv(
    "data/raw/measurements.csv",
    dtype={"site_id": "category", "value": "float32"},
    parse_dates=["timestamp"],
    usecols=["site_id", "timestamp", "value", "quality"],
)

# Chunked reading for large files
chunks = pd.read_csv("data/raw/large.csv", chunksize=50_000)
df = pd.concat(
    chunk[chunk["quality"] > 0] for chunk in chunks
)

# Parquet (preferred for intermediate data — columnar, typed, fast)
df.to_parquet("data/processed/clean.parquet", index=False)
df = pd.read_parquet("data/processed/clean.parquet")

# Multiple files
from pathlib import Path
files = Path("data/raw").glob("*.csv")
df = pd.concat(pd.read_csv(f) for f in files, ignore_index=True)
```

### Memory Optimization
```python
# Downcast numeric types
df["value"] = pd.to_numeric(df["value"], downcast="float")
df["count"] = pd.to_numeric(df["count"], downcast="integer")

# Use categoricals for low-cardinality strings
df["region"] = df["region"].astype("category")

# Check memory usage
print(df.memory_usage(deep=True).sum() / 1e6, "MB")
```

## Feature Engineering

### sklearn Pipeline Pattern
```python
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer

# Define column groups
numeric_features = ["elevation", "slope", "ndvi"]
categorical_features = ["land_use", "soil_type"]

# Build preprocessing pipeline
numeric_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
])

categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
])

preprocessor = ColumnTransformer([
    ("num", numeric_transformer, numeric_features),
    ("cat", categorical_transformer, categorical_features),
])

# Full pipeline with model
from sklearn.ensemble import RandomForestRegressor

model_pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("model", RandomForestRegressor(n_estimators=100, random_state=42)),
])

# Fit and predict
model_pipeline.fit(X_train, y_train)
predictions = model_pipeline.predict(X_test)
```

### Custom Transformers
```python
from sklearn.base import BaseEstimator, TransformerMixin

class LogTransformer(BaseEstimator, TransformerMixin):
    """Log-transform skewed features with offset for zeros."""

    def __init__(self, offset: float = 1.0):
        self.offset = offset

    def fit(self, X, y=None):
        return self  # Nothing to learn

    def transform(self, X):
        import numpy as np
        return np.log(X + self.offset)

    def inverse_transform(self, X):
        import numpy as np
        return np.exp(X) - self.offset
```

## Model Evaluation

### Cross-Validation
```python
from sklearn.model_selection import cross_val_score, KFold

# Standard k-fold
scores = cross_val_score(
    model_pipeline, X, y,
    cv=KFold(n_splits=5, shuffle=True, random_state=42),
    scoring="r2",
)
print(f"R² = {scores.mean():.3f} ± {scores.std():.3f}")

# Multiple metrics
from sklearn.model_selection import cross_validate

results = cross_validate(
    model_pipeline, X, y,
    cv=5,
    scoring=["r2", "neg_mean_absolute_error", "neg_root_mean_squared_error"],
    return_train_score=True,
)
for metric in ["test_r2", "test_neg_mean_absolute_error"]:
    vals = results[metric]
    print(f"{metric}: {vals.mean():.3f} ± {vals.std():.3f}")
```

### Spatial Cross-Validation
```python
# CRITICAL: Standard k-fold leaks spatial autocorrelation
# Use spatial CV for geospatial data

from sklearn.model_selection import GroupKFold

# Group by spatial blocks (e.g., grid cells, regions)
spatial_cv = GroupKFold(n_splits=5)
scores = cross_val_score(
    model_pipeline, X, y,
    cv=spatial_cv,
    groups=df["spatial_block"],
    scoring="r2",
)
```

### Train/Test Leakage Prevention
```python
# ALWAYS split BEFORE fitting preprocessors
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Pipeline handles this correctly — fit_transform on train, transform on test
# NEVER do this:
#   scaler.fit_transform(X)  # Leaks test statistics into training
#   X_train, X_test = split(X)

# DO this:
model_pipeline.fit(X_train, y_train)  # Preprocessor fits on train only
y_pred = model_pipeline.predict(X_test)  # Preprocessor transforms test
```

## Visualization

### matplotlib Figure/Axes Pattern
```python
import matplotlib.pyplot as plt
import numpy as np

# ALWAYS use the explicit OO interface (fig, ax), not plt.plot()
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(y_test, y_pred, alpha=0.5, s=20)
ax.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()],
        "r--", lw=2, label="1:1 line")
ax.set_xlabel("Observed")
ax.set_ylabel("Predicted")
ax.set_title("Model Performance")
ax.legend()
fig.tight_layout()
fig.savefig("reports/figures/model_performance.png", dpi=150, bbox_inches="tight")
plt.close(fig)  # Free memory — essential in loops/scripts
```

### Multi-Panel Figures
```python
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

axes[0].hist(y_train, bins=30, edgecolor="black")
axes[0].set_title("Distribution")

axes[1].scatter(y_test, y_pred, alpha=0.5)
axes[1].set_title("Predicted vs Observed")

residuals = y_test - y_pred
axes[2].scatter(y_pred, residuals, alpha=0.5)
axes[2].axhline(y=0, color="r", linestyle="--")
axes[2].set_title("Residuals")

fig.suptitle("Model Diagnostics", fontsize=14)
fig.tight_layout()
fig.savefig("reports/figures/diagnostics.png", dpi=150, bbox_inches="tight")
plt.close(fig)
```

### seaborn for Statistical Plots
```python
import seaborn as sns

# Correlation heatmap
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(df[numeric_features].corr(), annot=True, fmt=".2f",
            cmap="coolwarm", center=0, ax=ax)
fig.tight_layout()

# Pair plot (exploratory — expensive for >5 features)
g = sns.pairplot(df[numeric_features + ["target"]], hue="target",
                 diag_kind="kde", plot_kws={"alpha": 0.5})
g.savefig("reports/figures/pairplot.png", dpi=100)
```

## Reproducibility

### Random Seeds
```python
import numpy as np

# Set seeds at the TOP of scripts/notebooks
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# Pass seeds explicitly to all random operations
from sklearn.model_selection import train_test_split
X_train, X_test = train_test_split(X, y, random_state=RANDOM_SEED)

from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor(n_estimators=100, random_state=RANDOM_SEED)
```

### Configuration Files
```python
# config.py or config.yaml — centralize all parameters
from dataclasses import dataclass

@dataclass
class ExperimentConfig:
    random_seed: int = 42
    test_size: float = 0.2
    n_estimators: int = 100
    cv_folds: int = 5
    target_column: str = "value"
    feature_columns: list[str] | None = None

    def save(self, path: str) -> None:
        import json
        from pathlib import Path
        Path(path).write_text(json.dumps(self.__dict__, indent=2))

    @classmethod
    def load(cls, path: str) -> "ExperimentConfig":
        import json
        from pathlib import Path
        return cls(**json.loads(Path(path).read_text()))
```

### Data Versioning
```python
# Track data versions with checksums
import hashlib
from pathlib import Path

def file_checksum(path: str | Path) -> str:
    """SHA-256 checksum for data provenance."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

# Log in experiment metadata
data_hash = file_checksum("data/raw/measurements.csv")
# Save alongside model: {"data_hash": "a1b2c3d4e5f6", ...}
```

## Jupyter Best Practices

### Import From src/
```python
# In notebooks, ALWAYS import from src/ modules — don't duplicate logic in cells

# First cell of every notebook:
import sys
sys.path.insert(0, "..")  # Add project root to path

from src.data.loader import load_measurements
from src.features.engineering import build_feature_pipeline
from src.visualization.plots import plot_model_diagnostics
```

### Notebook Naming Convention
```
notebooks/
  01-data-exploration.ipynb       # EDA, data quality checks
  02-feature-engineering.ipynb    # Feature creation and selection
  03-model-training.ipynb         # Model fitting and tuning
  04-evaluation.ipynb             # Final evaluation and reporting
  05-spatial-analysis.ipynb       # Domain-specific analysis
```

### Notebook Hygiene
```python
# Use nbstripout to prevent committing outputs
# Install: pip install nbstripout && nbstripout --install

# Restart kernel and run all before committing
# Keep notebooks linear — no out-of-order execution

# Cell 1: Imports and configuration
# Cell 2: Data loading
# Cell 3-N: Analysis steps
# Last cell: Summary / key findings as markdown
```

## Common Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Logic in notebook cells | Extract to `src/` modules, import in notebooks |
| `df.apply(lambda x: ...)` for vectorizable ops | Use vectorized pandas/NumPy operations |
| Fitting preprocessor on full dataset | Always `fit` on train, `transform` on test (use Pipeline) |
| Standard k-fold for spatial data | Use `GroupKFold` or spatial blocking |
| `plt.show()` in scripts | Use `fig.savefig()` + `plt.close(fig)` |
| Hardcoded paths in notebooks | Use `Path` objects relative to project root |
| No random seeds | Set `random_state=42` on every random operation |
| Giant monolithic notebooks | Split into numbered stages, import from `src/` |
| `from module import *` | Import specific names |
| Ignoring dtypes on load | Specify `dtype` in `read_csv` for memory + correctness |
