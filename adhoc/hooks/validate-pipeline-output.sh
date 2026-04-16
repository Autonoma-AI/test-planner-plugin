#!/bin/bash
# Validates ad hoc planner output files after Write tool use.
# Exit 0 = allow (file is valid or not a pipeline file)
# Exit 2 = block and send error message to Claude

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALIDATORS_DIR="$SCRIPT_DIR/validators"

PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
echo "$PLUGIN_ROOT" > /tmp/autonoma-plugin-root

python3 -c "import yaml" 2>/dev/null || pip3 install pyyaml -q 2>/dev/null

case "$FILE_PATH" in
  */autonoma/qa-tests/*/INDEX.md)
    VALIDATOR_SCRIPT="$VALIDATORS_DIR/validate_test_index.py"
    VALIDATOR_NAME="validate-test-index"
    ;;
  */autonoma/qa-tests/*/[!I]*.md)
    VALIDATOR_SCRIPT="$VALIDATORS_DIR/validate_test_file.py"
    VALIDATOR_NAME="validate-test-file"
    ;;
  *)
    exit 0
    ;;
esac

if [ ! -f "$FILE_PATH" ]; then
  echo "VALIDATION FAILED [$VALIDATOR_NAME]: File does not exist: $FILE_PATH" >&2
  exit 2
fi

if [ ! -s "$FILE_PATH" ]; then
  echo "VALIDATION FAILED [$VALIDATOR_NAME]: File is empty: $FILE_PATH" >&2
  exit 2
fi

if [ ! -f "$VALIDATOR_SCRIPT" ]; then
  echo "VALIDATION FAILED [$VALIDATOR_NAME]: Validator script not found: $VALIDATOR_SCRIPT" >&2
  exit 2
fi

RESULT=$(python3 "$VALIDATOR_SCRIPT" "$FILE_PATH" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ] || [ "$RESULT" != "OK" ]; then
  echo "VALIDATION FAILED [$VALIDATOR_NAME]: $RESULT" >&2
  exit 2
fi

if [ "$VALIDATOR_NAME" = "validate-test-index" ]; then
  DIR_SCRIPT="$VALIDATORS_DIR/validate_directory_structure.py"
  DIR_RESULT=$(python3 "$DIR_SCRIPT" "$FILE_PATH" 2>&1)
  DIR_EXIT=$?
  if [ $DIR_EXIT -ne 0 ] || [ "$DIR_RESULT" != "OK" ]; then
    echo "VALIDATION FAILED [validate-directory-structure]: $DIR_RESULT" >&2
    exit 2
  fi
fi

exit 0
