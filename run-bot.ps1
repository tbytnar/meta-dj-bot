$ErrorActionPreference= 'silentlycontinue'

Write-Output "Checking for pre-requisties"
if(!git --version)
{
    Write-Output "Git is not installed.  Download and install it here: https://git-scm.com/download/win"
    exit
}
if(!tesseract --version)
{
    Write-Output "Tesseract is not installed.  Download and install it here: https://github.com/UB-Mannheim/tesseract/wiki"
    exit
}
if(!python --version)
{
    Write-Output "Python is not installed.  Download and install it here: https://www.python.org/downloads/"
    exit
}

Write-Output "Grabbing any updates"
git pull
pip install -r .\requirements.txt

Write-Output "Running Bot..."
python .\meta_spotify_dj.py