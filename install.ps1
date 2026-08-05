param(
    [string]$Target = "",
    [switch]$Force
)

$arguments = @("$PSScriptRoot\install.py")
if ($Target) {
    $arguments += @("--target", $Target)
}
if ($Force) {
    $arguments += "--force"
}
python @arguments
exit $LASTEXITCODE
