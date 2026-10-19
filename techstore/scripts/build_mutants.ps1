# ==============================================================================
# TechStore Mutant Container Image Tagging Script
# Builds 11 immutable container tags: techstore:clean, techstore:m01..m10
# ==============================================================================

param (
    [string]$Target = "all"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$techstoreDir = Split-Path -Parent $scriptDir

Write-Host "Building TechStore immutable container variants in: $techstoreDir" -ForegroundColor Cyan

function Build-Image {
    param (
        [string]$TagName,
        [string]$MutantId
    )
    Write-Host "------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "Building $TagName (MUTANT='$MutantId')..." -ForegroundColor Yellow
    if ($MutantId -eq "" -or $MutantId -eq "CLEAN") {
        docker build -t $TagName -f "$techstoreDir/Dockerfile" "$techstoreDir"
    } else {
        docker build --build-arg "MUTANT=$MutantId" -t $TagName -f "$techstoreDir/Dockerfile" "$techstoreDir"
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build image $TagName"
    }
    Write-Host "Successfully built $TagName" -ForegroundColor Green
}

# Image Tags definition
$allTags = @(
    @{ Tag = "techstore:clean"; Mutant = "" },
    @{ Tag = "techstore:m01"; Mutant = "M01" },
    @{ Tag = "techstore:m02"; Mutant = "M02" },
    @{ Tag = "techstore:m03"; Mutant = "M03" },
    @{ Tag = "techstore:m04"; Mutant = "M04" },
    @{ Tag = "techstore:m05"; Mutant = "M05" },
    @{ Tag = "techstore:m06"; Mutant = "M06" },
    @{ Tag = "techstore:m07"; Mutant = "M07" },
    @{ Tag = "techstore:m08"; Mutant = "M08" },
    @{ Tag = "techstore:m09"; Mutant = "M09" },
    @{ Tag = "techstore:m10"; Mutant = "M10" }
)

if ($Target -eq "all") {
    foreach ($entry in $allTags) {
        Build-Image -TagName $entry.Tag -MutantId $entry.Mutant
    }
    Write-Host "`nAll 11 TechStore container variants built and tagged successfully!" -ForegroundColor Green
} else {
    $matched = $allTags | Where-Object { $_.Tag -like "*$Target*" }
    if ($matched) {
        foreach ($entry in $matched) {
            Build-Image -TagName $entry.Tag -MutantId $entry.Mutant
        }
    } else {
        Write-Error "Target '$Target' did not match any known tags."
    }
}
