#!/usr/bin/env pwsh
# Migration Helper Script
# Finds all files using faker or moment that need updating

Write-Host "🔍 Searching for files that need migration..." -ForegroundColor Cyan
Write-Host ""

# Change to UI directory
Set-Location $PSScriptRoot

# Find faker usage
Write-Host "📦 Files using 'faker' (need @faker-js/faker migration):" -ForegroundColor Yellow
$fakerFiles = Get-ChildItem -Recurse -Include *.ts,*.tsx,*.js,*.jsx | 
    Where-Object { $_.FullName -notmatch "node_modules" } |
    Select-String -Pattern "from ['""]faker['""]" |
    Select-Object -ExpandProperty Path -Unique

if ($fakerFiles) {
    $fakerFiles | ForEach-Object {
        Write-Host "  - $_" -ForegroundColor White
    }
    Write-Host "  Total: $($fakerFiles.Count) files" -ForegroundColor Green
} else {
    Write-Host "  ✅ No faker imports found" -ForegroundColor Green
}

Write-Host ""

# Find moment usage
Write-Host "📅 Files using 'moment' (need date-fns migration):" -ForegroundColor Yellow
$momentFiles = Get-ChildItem -Recurse -Include *.ts,*.tsx,*.js,*.jsx | 
    Where-Object { $_.FullName -notmatch "node_modules" } |
    Select-String -Pattern "from ['""]moment['""]" |
    Select-Object -ExpandProperty Path -Unique

if ($momentFiles) {
    $momentFiles | ForEach-Object {
        Write-Host "  - $_" -ForegroundColor White
    }
    Write-Host "  Total: $($momentFiles.Count) files" -ForegroundColor Green
} else {
    Write-Host "  ✅ No moment imports found" -ForegroundColor Green
}

Write-Host ""

# Find @headlessui v1 usage patterns
Write-Host "🎨 Files using @headlessui/react (check for v1 → v2 changes):" -ForegroundColor Yellow
$headlessuiFiles = Get-ChildItem -Recurse -Include *.ts,*.tsx,*.js,*.jsx | 
    Where-Object { $_.FullName -notmatch "node_modules" } |
    Select-String -Pattern "from ['""]@headlessui/react['""]" |
    Select-Object -ExpandProperty Path -Unique

if ($headlessuiFiles) {
    $headlessuiFiles | ForEach-Object {
        Write-Host "  - $_" -ForegroundColor White
    }
    Write-Host "  Total: $($headlessuiFiles.Count) files" -ForegroundColor Green
} else {
    Write-Host "  ✅ No @headlessui imports found" -ForegroundColor Green
}

Write-Host ""

# Find @heroicons v1 usage patterns
Write-Host "🎭 Files using @heroicons/react (check for /outline → /24/outline):" -ForegroundColor Yellow
$heroiconsPattern = "@heroicons/react/(outline|solid)"
$heroiconsFiles = Get-ChildItem -Recurse -Include *.ts,*.tsx,*.js,*.jsx | 
    Where-Object { $_.FullName -notmatch "node_modules" } |
    Select-String -Pattern $heroiconsPattern |
    Select-Object -ExpandProperty Path -Unique

if ($heroiconsFiles) {
    $heroiconsFiles | ForEach-Object {
        Write-Host "  - $_" -ForegroundColor White
    }
    Write-Host "  Total: $($heroiconsFiles.Count) files" -ForegroundColor Green
} else {
    Write-Host "  ℹ️  No old @heroicons imports found (may already be v2)" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "✅ Scan complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run: npm install" -ForegroundColor White
Write-Host "  2. Update faker imports in the files listed above" -ForegroundColor White
Write-Host "  3. Update moment imports in the files listed above" -ForegroundColor White
Write-Host "  4. Check @headlessui and @heroicons imports" -ForegroundColor White
Write-Host "  5. Run: npm run type-check" -ForegroundColor White
Write-Host "  6. Run: npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "See MIGRATION_GUIDE.md for detailed conversion instructions." -ForegroundColor Cyan
