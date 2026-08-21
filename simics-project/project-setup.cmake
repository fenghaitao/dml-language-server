# Restrict module discovery to this project only.
# Without this, simics_find_and_add_modules() also scans IN_PACKAGES,
# pulling in all ~89 Simics sample devices from the install — which bloats
# the DML compile commands JSON and slows down the generate-dml-compile-commands
# target unnecessarily.
set(WHERE_TO_GLOB_FOR_MODULES IN_PROJECT)
