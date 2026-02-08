param(
    [string]$StackName = "DataLakeIncidentStack"
)

cd $PSScriptRoot\..

python -m venv .venv
. .\.venv\Scripts\Activate.ps1

pip install -r infra\requirements.txt

cdk synth
cdk deploy $StackName
