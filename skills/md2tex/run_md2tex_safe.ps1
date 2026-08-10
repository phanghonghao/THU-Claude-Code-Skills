param(
  [Parameter(Mandatory=$true)][string]$InputMd,
  [string]$OutputDir = '',
  [switch]$FixMathBackticks
)
$pre=Join-Path $PSScriptRoot 'md_math_precheck.py'
$core=Join-Path $PSScriptRoot 'md2tex.py'
if($FixMathBackticks){
  python $pre $InputMd --fix
}else{
  python $pre $InputMd
  if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
}
if([string]::IsNullOrWhiteSpace($OutputDir)){
  python $core $InputMd
}else{
  python $core $InputMd --output-dir $OutputDir
}
