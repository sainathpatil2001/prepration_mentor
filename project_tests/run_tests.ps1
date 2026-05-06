param(
    [string]$TestLabel = "project_tests",
    [switch]$VerboseOutput
)

$verbosity = if ($VerboseOutput) { 2 } else { 1 }

python manage.py test $TestLabel --verbosity $verbosity

