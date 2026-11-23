param([string]$Target = "$env:USERPROFILE\.agents\skills")
$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "skills"
New-Item -ItemType Directory -Force -Path $Target | Out-Null

$skills = Get-ChildItem $src -Recurse -Filter SKILL.md |
  Where-Object { $_.Directory.Parent.Parent.FullName -eq (Resolve-Path $src).Path }

  $seen = @{}
  foreach ($f in $skills) {
  	  $name = $f.Directory.Name
  	    if ($seen.ContainsKey($name)) { Write-Warning "duplikat nazwy '$name': $($f.FullName)"; continue }
  	      $seen[$name] = $true
  	        $dest = Join-Path $Target $name
  	          if (Test-Path $dest) {
  	          	    $it = Get-Item $dest -Force
  	          	        if ($it.LinkType) { Remove-Item $dest -Force }
  	          	            else { Write-Warning "pomijam '$name' — istnieje realny katalog"; continue }
  	          	              }
  	          	                New-Item -ItemType Junction -Path $dest -Target $f.Directory.FullName | Out-Null
  	          	                }
  	          	                Write-Host "Zsynchronizowano $($seen.Count) skilli."

  	          	                Get-ChildItem $Target -Force | Where-Object LinkType | ForEach-Object {
  	          	                	  if (-not (Test-Path (Join-Path $_.Target 'SKILL.md'))) {
  	          	                	  	    Remove-Item $_.FullName -Force; Write-Host "usunieto sierote: $($_.Name)"
  	          	                	  	      }
  	          	                	  	      }
  	          	                }
  	          }
  }
