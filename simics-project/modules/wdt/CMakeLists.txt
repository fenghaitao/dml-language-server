# © 2023 Intel Corporation

simics_add_module(wdt
  CLASSES wdt
  SOURCES wdt.dml module_load.py
  SIMICS_API 7
)
add_subdirectory(test)
