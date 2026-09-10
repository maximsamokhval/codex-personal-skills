Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-CodexSkillsDirectory {
    if ($env:CODEX_SKILLS_DIR) {
        return $env:CODEX_SKILLS_DIR
    }

    $homeDir = if ($HOME) { $HOME } elseif ($env:USERPROFILE) { $env:USERPROFILE } else { throw 'Не визначено HOME або USERPROFILE.' }
    $codexRoot = Join-Path $homeDir '.codex'
    $agentsRoot = Join-Path $homeDir '.agents'

    if ((Test-Path -LiteralPath $codexRoot -PathType Container) -or -not (Test-Path -LiteralPath $agentsRoot -PathType Container)) {
        return (Join-Path $codexRoot 'skills')
    }

    return (Join-Path $agentsRoot 'skills')
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourceRoot = Join-Path $repoRoot 'skills'
if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "Не знайдено skills у репозиторії: $sourceRoot"
}

$targetRoot = Get-CodexSkillsDirectory
New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("codex-personal-skills-{0}" -f [guid]::NewGuid())
New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null

$sourceSkills = @(Get-ChildItem -LiteralPath $sourceRoot -Directory)
if ($sourceSkills.Count -eq 0) {
    throw 'У репозиторії немає директорій skills для встановлення.'
}
$installedNames = @()

try {
    foreach ($skill in $sourceSkills) {
        $skillFile = Join-Path $skill.FullName 'SKILL.md'
        if (-not (Test-Path -LiteralPath $skillFile -PathType Leaf)) {
            throw "У skill відсутній SKILL.md: $($skill.Name)"
        }

        Copy-Item -LiteralPath $skill.FullName -Destination $stagingRoot -Recurse -Force
        if (-not (Test-Path -LiteralPath (Join-Path (Join-Path $stagingRoot $skill.Name) 'SKILL.md') -PathType Leaf)) {
            throw "Не вдалося підготувати skill: $($skill.Name)"
        }
    }

    # Старі копії лишаються у staging до успішної перевірки всіх нових skills.
    foreach ($skill in $sourceSkills) {
        $destination = Join-Path $targetRoot $skill.Name
        $backup = Join-Path $stagingRoot ('.backup-' + $skill.Name)
        if (Test-Path -LiteralPath $destination) {
            Move-Item -LiteralPath $destination -Destination $backup -Force
        }
        Move-Item -LiteralPath (Join-Path $stagingRoot $skill.Name) -Destination $destination -Force
        $installedNames += $skill.Name
    }

    foreach ($skill in $sourceSkills) {
        $destination = Join-Path $targetRoot $skill.Name
        if (-not (Test-Path -LiteralPath $destination -PathType Container)) {
            throw "Відсутня директорія встановленого skill: $($skill.Name)"
        }
        if (-not (Test-Path -LiteralPath (Join-Path $destination 'SKILL.md') -PathType Leaf)) {
            throw "У встановленому skill відсутній SKILL.md: $($skill.Name)"
        }
    }

    foreach ($skill in $sourceSkills) {
        $backup = Join-Path $stagingRoot ('.backup-' + $skill.Name)
        if (Test-Path -LiteralPath $backup) {
            Remove-Item -LiteralPath $backup -Recurse -Force
        }
    }

    Write-Host "Цільовий каталог: $targetRoot"
    Write-Host 'Встановлені skills:'
    $sourceSkills | ForEach-Object { Write-Host "  - $($_.Name)" }
}
catch {
    foreach ($skill in $sourceSkills) {
        $destination = Join-Path $targetRoot $skill.Name
        $backup = Join-Path $stagingRoot ('.backup-' + $skill.Name)
        if (Test-Path -LiteralPath $backup) {
            if (Test-Path -LiteralPath $destination) {
                Remove-Item -LiteralPath $destination -Recurse -Force
            }
            Move-Item -LiteralPath $backup -Destination $destination -Force
        }
        elseif (($installedNames -contains $skill.Name) -and (Test-Path -LiteralPath $destination)) {
            Remove-Item -LiteralPath $destination -Recurse -Force
        }
    }
    throw
}
finally {
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}
