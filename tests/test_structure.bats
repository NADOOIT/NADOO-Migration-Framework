#!/usr/bin/env bats

@test "Check main directory structure" {
  run ls -1
  [ "$status" -eq 0 ]
  [[ "$output" =~ "nadoo_migration_framework" ]]
}

@test "Check nadoo_migration_framework contents" {
  run ls -1 nadoo_migration_framework
  [ "$status" -eq 0 ]
  [[ "$output" =~ "classes" ]]
  [[ "$output" =~ "functions" ]]
  [[ "$output" =~ "processes" ]]
}

@test "Check for snake_case naming" {
  run find nadoo_migration_framework -type d -or -type f
  [ "$status" -eq 0 ]
  [[ ! "$output" =~ [A-Z] ]]
}
