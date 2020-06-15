# Author: Anton Ihonen
# Date: 2020

# The purpose of this script is to compile Kvazaar on Windows.
#
# Usage: kvazaar_compile.bat <%1> <%2> <%3> <%4>
# %1 The full path of the Visual Studio setup script (called VsDevCmd.bat)
# %2 The full path of the Kvazaar Visual Studio solution file (kvazaar\build\kvazaar_VS2015.sln or something similar)
# %3 The full destination path of the Kvazaar executable (i.e. where the executable will be located after compilation).
# %4 Build arguments to be passed to msbuild. These should include at least:
#  - /p:Configuration
#  - /p:Platform
#  - /p:WindowsTargetPlatformVersion (i.e. Windows SDK version)
#  - /p:PlatformToolSet
#
# Returns zero on success, non-zero otherwise.

$this_file_name = "kvazaar_compile_windows10.ps1"

Write-Output "--INFO: Running ${this_file_name}"

# Validate arguments.

if ("--help", "help", "-h", "--h" -Contains $Args[0])
{
    Write-Output "Usage: $this_file_name <VsDevCmd.bat filepath> <Kvazaar VS solution filepath> <msbuild arguments>"
    exit 0
}

if (!$Args[0])
{
    Write-Output "--ERROR: ${this_file_name}: Argument 1 (Visual Studio environment setup script path) is empty"
    exit 1
}
elseif (!(Split-Path $Args[0] -IsAbsolute))
{
    Write-Output "--WARNING: ${this_file_name}: Argument 1 (Visual Studio environment setup script path) is not an absolute filepath"
}

if (!$Args[1])
{
    Write-Output "--ERROR: ${this_file_name}: Argument 2 (Kvazaar Visual Studio solution path) is empty"
    exit 1
}
elseif (!(Split-Path $Args[1] -IsAbsolute))
{
    Write-Output "--WARNING: ${this_file_name}: Argument 2 (Kvazaar Visual Studio solution path) is not an absolute filepath"
}

if (!$Args[2])
{
    Write-Output "--ERROR: ${this_file_name}: Argument 3 (Kvazaar executable destination path) is empty"
    exit 1
}
elseif ($(Test-Path $Args[2]))
{
    Write-Output "--ERROR: ${this_file_name}: File `'$($Args[2])`' already exists"
    exit 1
}

if (!$Args[3])
{
    Write-Output "--ERROR: ${this_file_name}: Argument 4 (msbuild arguments) is empty"
    exit 1
}

# The path of VsDevCmd.bat, i.e. the script that needs to be run to set up the Visual Studio developer command prompt.
$vs_setup_script_path = $Args[0]
# The path of the Kvazaar Visual Studio solution.
$vs_solution_path = $Args[1]
# The path of the Kvazaar Git repository.
$kvz_repo_path = Split-Path $(Split-Path $Args[1]) # strips the path by two levels
#$kvz_repo_path = Split-Path ${kvz_repo_path}
# The path of the initial compilation output (the Kvazaar executable).
$kvz_executable_src_path = "${kvz_repo_path}\bin\x64-Release\Kvazaar.exe"
# The path of the destination directory of the Kvazaar executable.
$kvz_executable_dest_dir_path = Split-Path $Args[2]
# The destination path of the Kvazaar executable, i.e. the path in which the executable will be found after compilation.
$kvz_executable_dest_path = $Args[2]
# The arguments to be passed to msbuild.
$msbuild_args = $Args[3]

# Command to set up the Visual Studio developer command prompt environment.
$vs_setup_script_command = "call `"${vs_setup_script_path}`""
# Command to build the Kvazaar Visual Studio solution.
$msbuild_command = "msbuild.exe `"${vs_solution_path}`" ${msbuild_args}"

# This needs to be run in CMD because VsDevCmd.bat sets up a bunch of environment variables that need to
# persist until the call to msbuild.
Write-Output "--INFO: ${this_file_name}: Compiling Kvazaar"
cmd.exe /C "(${vs_setup_script_command} && ${msbuild_command} && exit 0) || exit 1"
if (!$?) { exit 1 }

# Create the destination directory if it doesn't exist already.
if (!(Test-Path ${kvz_executable_dest_dir_path}))
{
    Write-Output "--INFO: ${this_file_name}: Creating directory ${kvz_executable_dest_dir_path}"
    New-Item -ItemType Directory -Force -Path "${kvz_executable_dest_dir_path}"
}

# Copy the executable to the destination directory.
Write-Output "--INFO ${this_file_name}: Copying ${kvz_executable_src_path} to ${kvz_executable_dest_path}"
Copy-Item -path ${kvz_executable_src_path} -destination ${kvz_executable_dest_path}

# Return error if the copying wasn't successful.
if (!(Test-Path ${kvz_executable_dest_path}))
{
    exit 1
}

exit 0
