# Component definition file Template Repository

The `McStas`/`McXtrace` code generator [`mccode-antlr`](https://github.com/McStasMcXtrace/mccode-antlr.git) can use [`pooch`](https://github.com/fantiando/pooch.git) to fetch component definition files from GitHub repositories which containan appropriate `pooch` registry file.
The registry file is a listing of (component) filename and file hash pairs, and should be updated whenever a file changes.
Rather than calculating and updating the hashes in the registry by hand, this template includes a GitHub Actions workflow to keep the file up to date for you.

You may need to modify either the Python script which produces the file,
located at `.github/register.py`,
or the workflow, `.github/workflows/register.yml`,
to produce the registry file for your use case.

## Workflow permissions
You may need to modify the permissions granted to workflow files in your cloned repository.
Under `Workflow permissions` at [settings/actions](../../settings/actions) ensure that `Read and write permissions` is selected.
