#!/usr/bin/env bats

@test "Check required directories exist" {
  run ls -1
  [ "$status" -eq 0 ]
  [[ "$output" =~ "src" ]]
  [[ "$output" =~ "tests" ]]
  [[ "$output" =~ ".nadoo" ]]
}

@test "Check required files exist" {
  run ls -1
  [ "$status" -eq 0 ]
  [[ "$output" =~ "pyproject.toml" ]]
  [[ "$output" =~ ".nadoo/config.toml" ]]
}

@test "Check for required tools" {
  run command -v poetry
  [ "$status" -eq 0 ]

  run command -v pytest
  [ "$status" -eq 0 ]

  run command -v black
  [ "$status" -eq 0 ]
}

@test "Check code style rules" {
  run black --check --line-length 100 --skip-string-normalization .
  [ "$status" -eq 0 ]
}
