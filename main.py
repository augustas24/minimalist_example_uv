"""Just a test of how registration mechanism works.."""

import os
from pathlib import Path

from chapkit import BaseConfig
from chapkit.api import AssessedStatus, MLServiceBuilder, MLServiceInfo, ModelMetadata, PeriodType
from chapkit.artifact import ArtifactHierarchy
from chapkit.ml import ShellModelRunner
from pydantic import Field


class MinimalistExampleUvConfig(BaseConfig):
    """Configuration for minimalist_example_uv."""

    prediction_periods: int = Field(
        default=3,
        description="Number of periods to predict into the future.",
    )

    # chap-core ecosystem convention: most disease-surveillance models
    # (EWARS and friends) take rainfall + mean_temperature as lagged
    # climate predictors, so `chapkit mlproject migrate` pins them here by default.
    # If this model doesn't use climate covariates, DELETE the whole
    # block below - BaseConfig's inherited default is an empty list.
    # To keep the field but change it, override per-config via
    # POST /api/v1/configs (don't edit here unless the new defaults are
    # genuinely the model's intended defaults).
    additional_continuous_covariates: list[str] = Field(
        default=["rainfall"],
        description="Continuous covariates to include as lagged predictors.",
    )


# Commands are rendered in ShellModelRunner's template vocabulary
# ({data_file}, {historic_file}, {future_file}, {output_file}, {geo_file}).
# ShellModelRunner substitutes those with workspace-root filenames at train /
# predict time. Literal paths `model` (your script saves/loads it; preserved
# across train -> predict via workspace copy) and `config.yml` (always written
# by chapkit from the config above) stay verbatim.
# config_format="chap_core" writes config.yml in chap-core's ModelConfiguration
# shape (prediction_periods + additional_continuous_covariates at the top level,
# remaining fields nested under user_option_values) so scripts ported from
# chap-models repos can read config["user_option_values"][...] unchanged.
runner: ShellModelRunner[MinimalistExampleUvConfig] = ShellModelRunner(
    train_command="python model.py train {data_file} model",
    predict_command="python model.py predict model {historic_file} {future_file} {output_file}",
    config_format="chap_core",
)

info = MLServiceInfo(
    id="minimalist-example-uv",
    display_name="Minimalist example (uv)",
    description="Just a test of how registration mechanism works.",
    model_metadata=ModelMetadata(
        author="augustas24",
        author_note="Just a test of how registration mechanism works.",
        author_assessed_status=AssessedStatus.red,
    ),
    period_type=PeriodType.monthly,
    required_covariates=["rainfall"],
)

hierarchy = ArtifactHierarchy(
    name="minimalist_example_uv",
    level_labels={0: "ml_training_workspace", 1: "ml_prediction"},
)

# Persistent SQLite database by default so artifacts, configs, and jobs
# survive container restarts. Override with DATABASE_URL for a different
# SQLite file or a hosted Postgres (e.g. when deployed next to chap-core).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/chapkit.db")
if DATABASE_URL.startswith("sqlite") and ":///" in DATABASE_URL:
    db_path = Path(DATABASE_URL.split("///")[1])
    db_path.parent.mkdir(parents=True, exist_ok=True)

app = (
    MLServiceBuilder(
        info=info,
        config_schema=MinimalistExampleUvConfig,
        hierarchy=hierarchy,
        runner=runner,
        database_url=DATABASE_URL,
    )
    # See compose.yml for chap-core self-registration env vars.
    .with_registration()
    .build()
)


if __name__ == "__main__":
    from chapkit.api import run_app

    run_app("main:app", host="0.0.0.0", port=9090)